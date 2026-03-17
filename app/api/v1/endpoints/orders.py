from pathlib import Path
from decimal import Decimal
from typing import Iterable

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authenticated_user_context,
    get_order_service,
    get_company_repository,
    get_company_logo_repository,
    get_user_repository,
    get_plan_repository,
    get_industry_profile_repository,
    get_file_storage_service,
    get_db,
)
from app.repositories.base_repository import RecordNotFoundError
from app.models.order_status import OrderStatusEnum, PaymentStatus
from app.schemas.order import (
    OrderCreateRequest,
    OrderCreatedResponse,
    OrderSummaryResponse,
    CompanyDetailsResponse,
    DocumentSummary,
    OrderListItem,
    PaginatedOrdersResponse,
    TimelineEntry,
    OrderDetailResponse,
)
from app.services.order_service import OrderService
from app.services.file_storage_service import FileStorageService
from app.services.exceptions import (
    FileStorageServiceException,
    FileSaveException,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_logo_repository import CompanyLogoRepository
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.industry_profile_repository import IndustryProfileRepository
from app.models.company import Company
from app.models.user import User, UserRole

router = APIRouter()

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}
MAX_LOGO_SIZE_MB = 5


def parse_naics_codes_input(naics_codes: list[str] | None, naics_code: str | None) -> list[str]:
    parsed_codes: list[str] = []

    for raw_entry in naics_codes or []:
        split_candidates: Iterable[str] = raw_entry.split(",") if "," in raw_entry else [raw_entry]
        for candidate in split_candidates:
            normalized = candidate.strip()
            if normalized:
                parsed_codes.append(normalized)

    if naics_code and naics_code.strip():
        parsed_codes.append(naics_code.strip())

    deduplicated_codes: list[str] = []
    seen_codes: set[str] = set()
    for code in parsed_codes:
        if code not in seen_codes:
            seen_codes.add(code)
            deduplicated_codes.append(code)

    return deduplicated_codes


def build_company_details_response(company: Company) -> CompanyDetailsResponse:
    profile = company.industry_profile
    naics_codes = [entry.code for entry in profile.naics_codes] if profile else []

    return CompanyDetailsResponse(
        id=company.id,
        name=company.name,
        logo_id=company.logo_id,
        province=profile.province if profile else None,
        business_description=profile.business_description if profile else None,
        naics_codes=naics_codes,
    )


@router.post(
    "",
    response_model=OrderCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service),
    company_repo: CompanyRepository = Depends(get_company_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    db: Session = Depends(get_db),
) -> OrderCreatedResponse:
    if request.plan_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="plan_id must be greater than 0"
        )
    
    if not request.user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_email is required"
        )
    
    if not request.full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="full_name is required"
        )
    
    if not request.jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jurisdiction is required"
        )
    
    try:
        plan = plan_repo.get_by_id(request.plan_id)
    except RecordNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan with id {request.plan_id} not found"
        )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan with id {request.plan_id} not found"
        )
    
    user = user_repo.get_by_email(request.user_email)
    
    if not user:
        user = User(
            email=request.user_email,
            full_name=request.full_name,
            role=UserRole.CUSTOMER.value,
        )
        user = user_repo.create(user)
    
    company = company_repo.get_by_name(request.full_name)
    if not company:
        company = Company(name=request.full_name)
        company = company_repo.create(company)
    
    total_amount = Decimal(plan.base_price)
    
    order = order_service.create_order(
        user_id=user.id,
        company_id=company.id,
        plan_id=plan.id,
        jurisdiction=request.jurisdiction,
        total_amount=total_amount,
        is_industry_specific=False,
    )
    
    return OrderCreatedResponse(
        order_id=order.id,
        status=order.order_status.order_status,
        created_at=order.created_at,
        message="Order created successfully"
    )


@router.patch(
    "/{order_id}/company-details",
    response_model=OrderSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update company details and upload logo",
)
async def update_company_details(
    order_id: int,
    company_name: str = Form(..., min_length=1),
    province: str = Form(..., min_length=2, max_length=50),
    naics_codes: list[str] | None = Form(None, description="NAICS code list"),
    naics_code: str | None = Form(None, description="Deprecated single NAICS code"),
    business_description: str | None = Form(None),
    logo: UploadFile | None = File(None),
    order_service: OrderService = Depends(get_order_service),
    company_repo: CompanyRepository = Depends(get_company_repository),
    company_logo_repo: CompanyLogoRepository = Depends(get_company_logo_repository),
    industry_profile_repo: IndustryProfileRepository = Depends(get_industry_profile_repository),
    file_storage: FileStorageService = Depends(get_file_storage_service),
    db: Session = Depends(get_db),
) -> OrderSummaryResponse:
    if order_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id must be greater than 0"
        )
    
    if not company_name or not company_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_name is required"
        )
    
    if not province or not province.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="province is required"
        )
    
    if not naics_codes or not any(code.strip() for code in naics_codes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="naics_codes is required"
        )
    
    try:
        order = order_service.get_order_with_relations(order_id)
    except RecordNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    naics_list = parse_naics_codes_input(naics_codes, naics_code)
    if not naics_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one NAICS code is required"
        )
    
    for code in naics_list:
        if len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid NAICS code: {code}. Must be exactly 6 digits"
            )

    industry_profile_repo.upsert_profile_and_codes(
        company_id=order.company.id,
        province=province,
        naics_codes=naics_list,
        business_description=business_description,
    )
    
    company = order.company
    company.name = company_name
    company_repo.update(company)
    
    if logo:
        extension = Path(logo.filename).suffix.lower()
        if extension not in ALLOWED_LOGO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Logo file type {extension} not supported. Allowed: {ALLOWED_LOGO_EXTENSIONS}"
            )
        
        file_content = await logo.read()
        size_mb = len(file_content) / (1024 * 1024)
        if size_mb > MAX_LOGO_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Logo file size exceeds {MAX_LOGO_SIZE_MB}MB limit"
            )
        
        try:
            logo_path = file_storage.save_logo(file_content, order_id, logo.filename)
            company_logo = company_logo_repo.create_logo(order_id, str(logo_path))
            
            company.logo_id = company_logo.id
            company_repo.update(company)
        except (FileStorageServiceException, FileSaveException) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save logo: {str(e)}"
            )
    
    order = order_service.get_order_with_relations(order_id)
    
    company_details = None
    if order.company:
        company_details = build_company_details_response(order.company)
    
    return _build_order_summary(order, company_details)


@router.get(
    "/{order_id}/summary",
    response_model=OrderSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve order summary",
)
def get_order_summary(
    order_id: int,
    order_service: OrderService = Depends(get_order_service),
    current_user: dict[str, int | str] = Depends(get_authenticated_user_context),
) -> OrderSummaryResponse:
    if order_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id must be greater than 0"
        )
    
    try:
        order = order_service.get_order_with_relations(order_id)
    except RecordNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    if not order.user or order.user.email != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )

    company_details = None
    if order.company:
        company_details = build_company_details_response(order.company)
    
    return _build_order_summary(order, company_details)


@router.get(
    "",
    response_model=PaginatedOrdersResponse,
    status_code=status.HTTP_200_OK,
    summary="List orders for a user",
)
def list_orders(
    user_id: int,
    query: str | None = None,
    order_status: OrderStatusEnum | None = None,
    page: int = 1,
    page_size: int = 20,
    order_service: OrderService = Depends(get_order_service),
) -> PaginatedOrdersResponse:
    try:
        orders, total = order_service.list_user_orders(
            user_id=user_id,
            page=page,
            page_size=page_size,
            order_status=order_status,
            query=query,
        )
    except RecordNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    items = [_build_order_list_item(order) for order in orders]
    total_pages = max(1, -(-total // page_size))

    return PaginatedOrdersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full order detail",
)
def get_order_detail(
    order_id: int,
    user_id: int,
    order_service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    try:
        order = order_service.get_order_with_relations(order_id)
    except RecordNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )

    if order.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )

    return _build_order_detail(order)


def _build_order_list_item(order) -> OrderListItem:
    profile = order.company.industry_profile if order.company else None
    naics_codes = [entry.code for entry in profile.naics_codes] if profile else []

    return OrderListItem(
        order_id=order.id,
        created_at=order.created_at,
        order_status=order.order_status.order_status,
        payment_status=order.order_status.payment_status,
        total_amount=order.total_amount,
        currency=order.order_status.currency,
        jurisdiction=order.jurisdiction,
        company_name=order.company.name if order.company else None,
        plan_name=order.plan.name if order.plan else None,
        naics_codes=naics_codes,
    )


def _build_order_detail(order) -> OrderDetailResponse:
    company_details = build_company_details_response(order.company) if order.company else None

    profile = order.company.industry_profile if order.company else None
    naics_codes = [entry.code for entry in profile.naics_codes] if profile else []

    document_summaries = [
        DocumentSummary(
            document_id=doc.document_id,
            access_token=doc.access_token,
            token_expires_at=doc.token_expires_at,
            generated_at=doc.generated_at,
            file_format=doc.file_format or "docx",
        )
        for doc in (order.documents or [])
    ]

    return OrderDetailResponse(
        order_id=order.id,
        created_at=order.created_at,
        completed_at=order.completed_at,
        jurisdiction=order.jurisdiction,
        total_amount=order.total_amount,
        is_industry_specific=order.is_industry_specific,
        company=company_details,
        plan_name=order.plan.name if order.plan else None,
        order_status=order.order_status.order_status,
        payment_status=order.order_status.payment_status,
        currency=order.order_status.currency,
        documents=document_summaries,
        timeline=_build_timeline(order),
        naics_codes=naics_codes,
    )


def _build_timeline(order) -> list[TimelineEntry]:
    order_status_val = order.order_status.order_status
    payment_status_val = order.order_status.payment_status

    payment_done = payment_status_val == PaymentStatus.PAID.value
    processing_done = order_status_val in {OrderStatusEnum.PROCESSING.value, OrderStatusEnum.AVAILABLE.value}
    completed_done = order_status_val == OrderStatusEnum.AVAILABLE.value

    return [
        TimelineEntry(
            step="Order Placed",
            status="completed",
            timestamp=order.created_at,
        ),
        TimelineEntry(
            step="Payment",
            status="completed" if payment_done else "pending",
            timestamp=None,
        ),
        TimelineEntry(
            step="Processing",
            status="completed" if processing_done else "pending",
            timestamp=None,
        ),
        TimelineEntry(
            step="Completed",
            status="completed" if completed_done else "pending",
            timestamp=order.completed_at,
        ),
    ]


def _build_order_summary(order, company_details: CompanyDetailsResponse | None) -> OrderSummaryResponse:
    document_summaries = [
        DocumentSummary(
            document_id=doc.document_id,
            access_token=doc.access_token,
            token_expires_at=doc.token_expires_at,
            generated_at=doc.generated_at,
            file_format=doc.file_format or "docx",
        )
        for doc in (order.documents or [])
    ]

    return OrderSummaryResponse(
        order_id=order.id,
        user_email=order.user.email,
        full_name=order.user.full_name,
        company=company_details,
        plan_name=order.plan.name if order.plan else None,
        jurisdiction=order.jurisdiction,
        total_amount=order.total_amount,
        order_status=order.order_status.order_status,
        payment_status=order.order_status.payment_status,
        created_at=order.created_at,
        completed_at=order.completed_at,
        is_industry_specific=order.is_industry_specific,
        documents=document_summaries,
    )
