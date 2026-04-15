import math
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi import Path as PathParam

from app.api.dependencies import (
    get_admin_auth_service,
    get_admin_order_service,
    get_admin_user_repository,
    get_authenticated_admin_context,
    get_email_log_repository,
    get_order_repository,
    get_owner_admin_context,
    get_plan_repository,
    get_sjp_generation_service,
    get_user_repository,
)
from app.models.order import Order
from app.repositories.admin_user_repository import AdminUserRepository
from app.repositories.email_log_repository import EmailLogRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminCustomerListItem,
    AdminDocumentSummary,
    AdminEmailLogItem,
    AdminNotesUpdateRequest,
    AdminOrderDetailResponse,
    AdminOrderListItem,
    AdminPaginatedCustomersResponse,
    AdminPaginatedEmailLogsResponse,
    AdminPaginatedOrdersResponse,
    AdminPlanResponse,
    AdminStaffListItem,
    AdminStatsResponse,
    CreateAdminUserRequest,
    OrderApproveRequest,
    PlanApprovalSettingRequest,
    PlanPriceUpdateRequest,
    TemplateListItem,
)
from app.schemas.sjp import SjpContentEditRequest, SjpFullContentResponse
from app.services.admin_auth_service import AdminAuthService
from app.services.admin_order_service import AdminOrderService
from app.services.admin_stats_service import AdminStatsService
from app.services.sjp_generation_service import (
    SjpGenerationJobNotFound,
    SjpGenerationService,
    OrderNotFound as SjpOrderNotFound,
)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / "templates" / "documents"


def _build_order_list_item(order: Order) -> AdminOrderListItem:
    os = order.order_status
    return AdminOrderListItem(
        order_id=order.id,
        created_at=order.created_at,
        order_status=os.order_status if os else "unknown",
        payment_status=os.payment_status if os else "unknown",
        total_amount=order.total_amount,
        currency=os.currency if os else "CAD",
        jurisdiction=order.jurisdiction,
        company_name=order.company.name if order.company else None,
        plan_name=order.plan.name if order.plan else None,
        user_email=order.user.email if order.user else None,
        user_full_name=order.user.full_name if order.user else None,
        is_industry_specific=order.is_industry_specific,
        admin_notes=order.admin_notes,
    )


def _build_order_detail(order: Order) -> AdminOrderDetailResponse:
    os = order.order_status
    documents = [
        AdminDocumentSummary(
            document_id=doc.document_id,
            access_token=doc.access_token,
            token_expires_at=doc.token_expires_at,
            generated_at=doc.generated_at,
            file_format=doc.file_format or "docx",
            downloaded_count=doc.downloaded_count or 0,
        )
        for doc in (order.documents or [])
    ]
    email_logs = [
        AdminEmailLogItem(
            id=log.id,
            order_id=log.order_id,
            recipient_email=log.recipient_email,
            subject=log.subject,
            status=log.status,
            sent_at=log.sent_at,
            failure_reason=log.failure_reason,
        )
        for log in (order.email_logs or [])
    ]

    return AdminOrderDetailResponse(
        order_id=order.id,
        created_at=order.created_at,
        completed_at=order.completed_at,
        reviewed_at=order.reviewed_at,
        reviewed_by_admin_id=order.reviewed_by_admin_id,
        jurisdiction=order.jurisdiction,
        total_amount=order.total_amount,
        is_industry_specific=order.is_industry_specific,
        admin_notes=order.admin_notes,
        company_name=order.company.name if order.company else None,
        plan_name=order.plan.name if order.plan else None,
        order_status=os.order_status if os else "unknown",
        payment_status=os.payment_status if os else "unknown",
        currency=os.currency if os else "CAD",
        user_email=order.user.email if order.user else None,
        user_full_name=order.user.full_name if order.user else None,
        documents=documents,
        email_logs=email_logs,
    )


# ── Order Management ──


@router.get(
    "/orders",
    response_model=AdminPaginatedOrdersResponse,
    status_code=status.HTTP_200_OK,
)
def list_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_status: str | None = Query(None),
    payment_status: str | None = Query(None),
    plan_id: int | None = Query(None),
    query: str | None = Query(None),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> AdminPaginatedOrdersResponse:
    orders, total = admin_order_service.get_all_orders_paginated(
        page=page,
        page_size=page_size,
        order_status=order_status,
        payment_status=payment_status,
        plan_id=plan_id,
        query=query,
    )
    return AdminPaginatedOrdersResponse(
        items=[_build_order_list_item(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/orders/pending-review",
    response_model=AdminPaginatedOrdersResponse,
    status_code=status.HTTP_200_OK,
)
def list_pending_review_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> AdminPaginatedOrdersResponse:
    orders, total = admin_order_service.get_pending_review_orders(page=page, page_size=page_size)
    return AdminPaginatedOrdersResponse(
        items=[_build_order_list_item(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/orders/{order_id}",
    response_model=AdminOrderDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_order_detail(
    order_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> AdminOrderDetailResponse:
    order = admin_order_service.get_order_detail(order_id)
    return _build_order_detail(order)


@router.post(
    "/orders/{order_id}/approve",
    response_model=AdminOrderDetailResponse,
    status_code=status.HTTP_200_OK,
)
def approve_order(
    order_id: int = PathParam(..., gt=0),
    body: OrderApproveRequest | None = None,
    admin_context: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> AdminOrderDetailResponse:
    if body and body.admin_notes:
        admin_order_service.update_admin_notes(order_id, body.admin_notes)

    order = admin_order_service.approve_order(order_id, admin_context["id"])
    return _build_order_detail(order)


@router.patch(
    "/orders/{order_id}/notes",
    response_model=AdminOrderDetailResponse,
    status_code=status.HTTP_200_OK,
)
def update_order_notes(
    body: AdminNotesUpdateRequest,
    order_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> AdminOrderDetailResponse:
    order = admin_order_service.update_admin_notes(order_id, body.admin_notes)
    return _build_order_detail(order)


@router.post(
    "/orders/{order_id}/resend-email",
    status_code=status.HTTP_200_OK,
)
def resend_order_email(
    order_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> dict[str, str]:
    admin_order_service.resend_delivery_email(order_id)
    return {"message": "delivery email resent"}


@router.post(
    "/orders/{order_id}/regenerate-document",
    status_code=status.HTTP_200_OK,
)
def regenerate_order_document(
    order_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    admin_order_service: AdminOrderService = Depends(get_admin_order_service),
) -> dict[str, str]:
    admin_order_service.regenerate_document(order_id)
    return {"message": "document regenerated"}


# ── Customer Viewing ──


@router.get(
    "/customers",
    response_model=AdminPaginatedCustomersResponse,
    status_code=status.HTTP_200_OK,
)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = Query(None),
    _admin: dict = Depends(get_authenticated_admin_context),
    user_repo: UserRepository = Depends(get_user_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
) -> AdminPaginatedCustomersResponse:
    from sqlalchemy import func

    from app.models.order import Order
    from app.models.user import User

    skip = (page - 1) * page_size
    base_q = user_repo.db.query(User)

    if query:
        base_q = base_q.filter(
            (User.email.ilike(f"%{query}%")) | (User.full_name.ilike(f"%{query}%"))
        )

    total = base_q.count()

    users = base_q.order_by(User.created_at.desc()).offset(skip).limit(page_size).all()

    items = []
    for user in users:
        order_count = order_repo.db.query(func.count(Order.id)).filter(Order.user_id == user.id).scalar()
        items.append(
            AdminCustomerListItem(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at,
                last_login=user.last_login,
                order_count=order_count or 0,
            )
        )

    return AdminPaginatedCustomersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/customers/{user_id}",
    response_model=AdminCustomerListItem,
    status_code=status.HTTP_200_OK,
)
def get_customer_detail(
    user_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    user_repo: UserRepository = Depends(get_user_repository),
    order_repo: OrderRepository = Depends(get_order_repository),
) -> AdminCustomerListItem:
    from sqlalchemy import func

    from app.models.order import Order

    user = user_repo.get_by_id_or_fail(user_id)
    order_count = order_repo.db.query(func.count(Order.id)).filter(Order.user_id == user.id).scalar()

    return AdminCustomerListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
        last_login=user.last_login,
        order_count=order_count or 0,
    )


# ── Plan Management ──


@router.get(
    "/plans",
    response_model=list[AdminPlanResponse],
    status_code=status.HTTP_200_OK,
)
def list_plans(
    _admin: dict = Depends(get_authenticated_admin_context),
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> list[AdminPlanResponse]:
    plans = plan_repo.get_all_plans()
    return [AdminPlanResponse.model_validate(p) for p in plans]


@router.patch(
    "/plans/{plan_id}/approval-setting",
    response_model=AdminPlanResponse,
    status_code=status.HTTP_200_OK,
)
def update_plan_approval_setting(
    body: PlanApprovalSettingRequest,
    plan_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_owner_admin_context),
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> AdminPlanResponse:
    plan = plan_repo.get_by_id_or_fail(plan_id)
    plan.requires_approval = body.requires_approval
    plan_repo.update(plan)
    return AdminPlanResponse.model_validate(plan)


@router.patch(
    "/plans/{plan_id}/price",
    response_model=AdminPlanResponse,
    status_code=status.HTTP_200_OK,
)
def update_plan_price(
    body: PlanPriceUpdateRequest,
    plan_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_owner_admin_context),
    plan_repo: PlanRepository = Depends(get_plan_repository),
) -> AdminPlanResponse:
    plan = plan_repo.update_base_price(plan_id, body.base_price)
    return AdminPlanResponse.model_validate(plan)


# ── Template Management ──


@router.get(
    "/templates",
    response_model=list[TemplateListItem],
    status_code=status.HTTP_200_OK,
)
def list_templates(
    _admin: dict = Depends(get_authenticated_admin_context),
) -> list[TemplateListItem]:
    if not TEMPLATES_DIR.exists():
        return []

    items = []
    for file_path in sorted(TEMPLATES_DIR.glob("*.docx")):
        slug = file_path.stem.replace("_manual_template", "")
        stat = file_path.stat()
        items.append(
            TemplateListItem(
                plan_slug=slug,
                filename=file_path.name,
                file_size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return items


@router.post(
    "/templates/{plan_slug}",
    status_code=status.HTTP_200_OK,
)
async def upload_template(
    plan_slug: str,
    file: UploadFile,
    _admin: dict = Depends(get_owner_admin_context),
) -> dict[str, str]:
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx files are accepted",
        )

    template_filename = f"{plan_slug}_manual_template.docx"
    target_path = TEMPLATES_DIR / template_filename

    if not TEMPLATES_DIR.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Templates directory not found",
        )

    content = await file.read()
    target_path.write_bytes(content)

    return {"message": f"template {template_filename} uploaded", "filename": template_filename}


@router.get(
    "/templates/{plan_slug}/download",
    status_code=status.HTTP_200_OK,
)
def download_template(
    plan_slug: str,
    _admin: dict = Depends(get_authenticated_admin_context),
):
    from fastapi.responses import FileResponse

    template_filename = f"{plan_slug}_manual_template.docx"
    file_path = TEMPLATES_DIR / template_filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_filename} not found",
        )

    return FileResponse(
        path=str(file_path),
        filename=template_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── Dashboard Stats ──


@router.get(
    "/stats/dashboard",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
)
def get_dashboard_stats(
    _admin: dict = Depends(get_authenticated_admin_context),
    order_repo: OrderRepository = Depends(get_order_repository),
) -> AdminStatsResponse:
    service = AdminStatsService(order_repo)
    stats = service.get_dashboard_stats()
    return AdminStatsResponse(**stats)


# ── Email Logs ──


@router.get(
    "/logs/emails",
    response_model=AdminPaginatedEmailLogsResponse,
    status_code=status.HTTP_200_OK,
)
def list_email_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    email_status: str | None = Query(None),
    order_id: int | None = Query(None),
    _admin: dict = Depends(get_authenticated_admin_context),
    email_log_repo: EmailLogRepository = Depends(get_email_log_repository),
) -> AdminPaginatedEmailLogsResponse:
    skip = (page - 1) * page_size
    logs, total = email_log_repo.get_all_paginated(
        skip=skip,
        limit=page_size,
        email_status=email_status,
        order_id=order_id,
    )
    return AdminPaginatedEmailLogsResponse(
        items=[AdminEmailLogItem.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ── SJP Content Review ──


@router.get(
    "/orders/{order_id}/sjp-content",
    response_model=SjpFullContentResponse,
    status_code=status.HTTP_200_OK,
)
def get_sjp_content_for_review(
    order_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> SjpFullContentResponse:
    try:
        return sjp_service.get_full_content(order_id=order_id, user_id=None)
    except (SjpOrderNotFound, SjpGenerationJobNotFound) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/sjp-content/{toc_entry_id}",
    status_code=status.HTTP_200_OK,
)
def edit_sjp_content(
    body: SjpContentEditRequest,
    toc_entry_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> dict:
    try:
        updates = body.model_dump(exclude_none=True)
        sjp_service.update_sjp_content(toc_entry_id, updates)
        return {"message": "content updated", "toc_entry_id": toc_entry_id}
    except SjpGenerationJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/sjp-content/{toc_entry_id}/regenerate",
    status_code=status.HTTP_200_OK,
)
async def regenerate_single_sjp(
    toc_entry_id: int = PathParam(..., gt=0),
    _admin: dict = Depends(get_authenticated_admin_context),
    sjp_service: SjpGenerationService = Depends(get_sjp_generation_service),
) -> dict:
    try:
        await sjp_service.regenerate_single_sjp(toc_entry_id)
        return {"message": "regeneration started", "toc_entry_id": toc_entry_id}
    except SjpGenerationJobNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Admin Staff Management (Owner only) ──


@router.get(
    "/staff",
    response_model=list[AdminStaffListItem],
    status_code=status.HTTP_200_OK,
)
def list_admin_staff(
    _admin: dict = Depends(get_owner_admin_context),
    admin_user_repo: AdminUserRepository = Depends(get_admin_user_repository),
) -> list[AdminStaffListItem]:
    admins, _ = admin_user_repo.get_all_paginated(skip=0, limit=100)
    return [AdminStaffListItem.model_validate(a) for a in admins]


@router.post(
    "/staff",
    response_model=AdminStaffListItem,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_staff(
    body: CreateAdminUserRequest,
    _admin: dict = Depends(get_owner_admin_context),
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminStaffListItem:
    try:
        result = admin_auth_service.create_admin_user(
            email=body.email,
            full_name=body.full_name,
            password=body.password,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    admin_user_repo = admin_auth_service.admin_user_repo
    admin = admin_user_repo.get_by_id_or_fail(result["id"])
    return AdminStaffListItem.model_validate(admin)


@router.patch(
    "/staff/{admin_id}/deactivate",
    response_model=AdminStaffListItem,
    status_code=status.HTTP_200_OK,
)
def deactivate_admin_staff(
    admin_id: int = PathParam(..., gt=0),
    owner: dict = Depends(get_owner_admin_context),
    admin_user_repo: AdminUserRepository = Depends(get_admin_user_repository),
) -> AdminStaffListItem:
    if admin_id == owner["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    admin = admin_user_repo.deactivate(admin_id)
    return AdminStaffListItem.model_validate(admin)
