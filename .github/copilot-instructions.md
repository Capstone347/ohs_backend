---
applyTo: '**'
---

# OHS Remote Backend - Coding Instructions

---

## Core Philosophy

This document defines the coding standards and practices for the OHS Remote backend codebase. These instructions prioritize maintainability, clarity, and long-term code health over short-term convenience. Every line of code should be written with the understanding that it will be read and modified by others.

---

## Universal Principles

### Separation of Concerns and Single Responsibility

Every function, class, and module should have one clear purpose. If a function performs multiple distinct actions, split it into smaller, focused functions.

**Good:**
```python
def process_order_workflow(order_id: str):
    order_data = fetch_order_details(order_id)
    validated_order = validate_order_requirements(order_data)
    generated_document = generate_document_from_template(validated_order)
    preview_document = create_blurred_preview(generated_document)
    return preview_document
```

**Bad:**
```python
def process_order_workflow(order_id: str):
    # Fetches, validates, generates, and creates preview all in one function
    order = db.query(Order).filter(Order.id == order_id).first()
    if order and order.company_name and order.naics_codes:
        doc = Document()
        # ... 50 lines of document generation
        preview = blur_document(doc)
        return preview
```

### Self-Documenting Code

Code should explain itself through clear naming and structure. Comments and docstrings are not needed and should be avoided.

**Use business-level function names:**
- `generate_document_preview()` not `make_doc()`
- `validate_naics_code()` not `check_code()`
- `send_document_delivery_email()` not `send_email()`
- `process_stripe_payment()` not `handle_payment()`

**Variable names should reveal intent:**
- `company_logo_path` not `path` or `logo`
- `order_total_amount` not `total` or `amount`
- `validated_naics_codes` not `codes` or `naics`
- `generated_document_path` not `doc_path` or `file`

### Data Structures Over Dictionaries

Dictionaries should be a last resort. They are difficult to refactor, lack type safety, and make code harder to understand and maintain.

**When dictionaries are acceptable:**
- Configuration data within a single file that is not shared
- Dynamic key-value pairs where keys are truly unknown at design time
- Direct mapping to external JSON/API responses (before transformation into models)

**When to use structured types instead:**
- Any data structure used across multiple files
- Function parameters and return values
- Data that represents domain entities (orders, documents, companies)
- Data that will be validated or transformed

### Antipattern: Result Dictionaries

Never return dictionaries with success flags or status indicators. Functions should be independent and their behavior clear from their signature.

**Bad:**
```python
def validate_order(order_data: dict):
    if not order_data.get("company_name"):
        return {"success": False, "error": "Missing company name"}
    return {"success": True, "order": order_data}
```

**Good:**
```python
def validate_order(order: Order) -> Order:
    if not order.company_name:
        raise ValidationError("Missing company name")
    return order
```

Use exceptions for errors and return the actual data for success cases. Let the caller handle the exception rather than forcing them to check dictionaries.

### Function Independence

Every function should be understandable without examining other parts of the codebase. Avoid implicit dependencies and hidden state.

**Bad:**
```python
def process_document():
    result = validate_template()
    if result["valid"]:
        return result["template"]
    else:
        handle_error(result["error"])
```

**Good:**
```python
def process_document(order: Order, template_path: str) -> Document:
    validated_template = validate_template(template_path)
    populated_document = populate_template(validated_template, order)
    return populated_document
```

---

## Python-Specific Guidelines

### Use Enums for Fixed Sets of Values

String comparisons are fragile and error-prone. Use enums for any fixed set of values.

**Bad:**
```python
if order_status == "paid":
    process_paid_order()
elif order_status == "pending":
    process_pending_order()
```

**Good:**
```python
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    PAYMENT_INITIATED = "payment_initiated"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

if order.status == OrderStatus.PAID:
    process_paid_order()
elif order.status == OrderStatus.PENDING:
    process_pending_order()
```

### Pydantic for Validation and Models

Use Pydantic for all data validation and model definition. This provides type safety, validation, and clear data contracts.

**Bad:**
```python
def create_order(order_data: dict):
    if "company_name" not in order_data:
        raise ValueError("Missing company_name")
    if not isinstance(order_data.get("naics_codes"), list):
        raise ValueError("NAICS codes must be a list")
```

**Good:**
```python
from pydantic import BaseModel, Field

class OrderCreateRequest(BaseModel):
    plan_id: str
    user_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    company_name: str = Field(..., min_length=1)

class OrderCompanyDetailsRequest(BaseModel):
    province: str
    naics_codes: list[str] = Field(..., min_items=1)
    
def create_order(request: OrderCreateRequest):
    # Validation happens automatically
    pass
```

### Modern Python Features

Use current Python features and avoid deprecated patterns.

- Use `list[str]` not `List[str]` (Python 3.9+)
- Use `dict[str, int]` not `Dict[str, int]` (Python 3.9+)
- Use `match`/`case` for complex conditionals (Python 3.10+)
- Use `|` for union types (Python 3.10+)
- Use structural pattern matching when appropriate

### Type Hints

All function signatures should include type hints for parameters and return values.

```python
from pathlib import Path

def generate_document(order: Order, template_path: Path) -> Path:
    document = create_document_from_template(template_path, order)
    output_path = save_document(document)
    return output_path
```

---

## Code Organization

### File Structure

- Each file should be understandable in 20 minutes or less
- If a file is too complex, split it into multiple files
- File names must clearly indicate their purpose
- Group related functionality into modules

**Example structure:**
```
app/
├── api/v1/endpoints/
│   ├── orders.py
│   ├── documents.py
│   └── payments.py
├── services/
│   ├── order_service.py
│   ├── document_generation_service.py
│   └── payment_service.py
├── repositories/
│   ├── order_repository.py
│   └── document_repository.py
└── models/
    ├── order.py
    └── document.py
```

### Function Composition

Break complex logic into smaller functions. Functions can call other functions within the same scope.

```python
def generate_complete_manual(order: Order) -> Path:
    validated_order = validate_order_completeness(order)
    template = load_appropriate_template(validated_order.plan)
    populated_document = populate_template_variables(template, validated_order)
    document_with_logo = insert_company_logo(populated_document, validated_order.logo_path)
    final_document_path = save_document(document_with_logo, validated_order.id)
    return final_document_path

def validate_order_completeness(order: Order) -> Order:
    validate_company_details(order.company)
    validate_plan_selection(order.plan)
    validate_jurisdiction(order.province)
    return order
```

---

## Design Considerations

### Anticipate Change

Think about what values or behaviors might change:
- Configuration values should be externalized
- Business rules should be isolated
- Magic numbers should be named constants
- Format strings should be templates

**Example:**
```python
# Bad - hardcoded values
if len(naics_code) != 6:
    raise ValueError("Invalid NAICS code")

# Good - named constants
NAICS_CODE_LENGTH = 6

def validate_naics_format(naics_code: str) -> bool:
    if len(naics_code) != NAICS_CODE_LENGTH:
        raise ValidationError(f"NAICS code must be exactly {NAICS_CODE_LENGTH} digits")
    return True
```

### Data Structure Selection

Before choosing a data structure, ask:
1. Will this be used in multiple places?
2. Does this represent a domain concept?
3. Will this need validation?
4. Could the structure change?

If yes to any of these, use a structured type (Pydantic model, dataclass, or named tuple) instead of a dictionary.

### Code Reusability

Identify patterns that will be reused:
- Extract common validation logic
- Create shared utility functions
- Build reusable transformers
- Design composable operations

---

## FastAPI Specific Guidelines

### Endpoint Structure

Keep endpoint handlers thin. They should only handle HTTP concerns, delegate business logic to services.

**Bad:**
```python
@router.post("/orders")
async def create_order(order_data: dict):
    # Validation logic
    if not order_data.get("company_name"):
        raise HTTPException(status_code=400, detail="Missing company name")
    
    # Business logic
    order = Order(**order_data)
    db.add(order)
    db.commit()
    
    # Email logic
    send_email(order.user_email, "Order created")
    
    return {"order_id": order.id}
```

**Good:**
```python
@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service)
) -> OrderResponse:
    order = order_service.create_order(request)
    return OrderResponse.from_orm(order)
```

### Dependency Injection

Use FastAPI's dependency injection for all services and repositories.

```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

def get_order_service(
    order_repo: OrderRepository = Depends(get_order_repository),
    email_service: EmailService = Depends(get_email_service)
) -> OrderService:
    return OrderService(order_repo, email_service)

@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service)
):
    return order_service.get_order(order_id)
```

### Request and Response Models

Always use Pydantic models for request and response bodies. Never use raw dictionaries.

```python
class OrderCreateRequest(BaseModel):
    plan_id: str
    user_email: str
    company_name: str

class OrderResponse(BaseModel):
    order_id: str
    status: OrderStatus
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy models

@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(request: OrderCreateRequest):
    # FastAPI automatically validates request
    pass
```

### Error Handling

Use FastAPI's exception handlers for consistent error responses.

**Define custom exceptions:**
```python
class OrderServiceException(Exception):
    pass

class OrderNotFoundError(OrderServiceException):
    pass

class InvalidNAICSCodeError(OrderServiceException):
    pass
```

**Register exception handlers:**
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "ORDER_NOT_FOUND", "message": str(exc)}}
    )

@app.exception_handler(InvalidNAICSCodeError)
async def invalid_naics_handler(request: Request, exc: InvalidNAICSCodeError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "INVALID_NAICS_CODE", "message": str(exc)}}
    )
```

### Async vs Sync

Be consistent with async/sync usage:
- Use `async def` for I/O-bound operations (database queries, external API calls, file operations)
- Use regular `def` for CPU-bound operations (document generation, image processing)
- Never mix blocking operations in async functions

**Good:**
```python
@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service)
):
    # Database query is async
    order = await order_service.get_order_async(order_id)
    return order
```

**Also acceptable when using sync libraries:**
```python
@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    order_service: OrderService = Depends(get_order_service)
):
    # SQLAlchemy sync operations
    order = order_service.get_order(order_id)
    return order
```

---

## SQLAlchemy and Database Guidelines

### Model Definition

Define models in `app/models/` with clear relationships and constraints.

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.base import Base
from datetime import datetime
import enum

class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    COMPLETED = "completed"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    company = relationship("Company", back_populates="orders")
    plan = relationship("Plan")
    documents = relationship("Document", back_populates="order")
```

### Repository Pattern

Isolate all database access in repository classes.

```python
from sqlalchemy.orm import Session
from app.models.order import Order, OrderStatus

class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        order = self.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(f"Order {order_id} not found")
        
        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def get_orders_by_user(self, user_id: int) -> list[Order]:
        return self.db.query(Order).filter(Order.user_id == user_id).all()
```

### Query Optimization

Always be mindful of N+1 query problems. Use eager loading when necessary.

**Bad - N+1 queries:**
```python
def get_orders_with_documents(user_id: int):
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    # Each order will trigger a separate query for documents
    for order in orders:
        documents = order.documents
```

**Good - Eager loading:**
```python
from sqlalchemy.orm import joinedload

def get_orders_with_documents(user_id: int):
    orders = db.query(Order)\
        .options(joinedload(Order.documents))\
        .filter(Order.user_id == user_id)\
        .all()
```

### Transaction Management

Keep transactions at the repository level. Let services orchestrate multiple repository calls.

```python
class OrderService:
    def __init__(self, order_repo: OrderRepository, document_repo: DocumentRepository):
        self.order_repo = order_repo
        self.document_repo = document_repo
    
    def complete_order(self, order_id: int, document_path: str):
        # Each repository handles its own transaction
        order = self.order_repo.update_status(order_id, OrderStatus.COMPLETED)
        document = self.document_repo.create_for_order(order_id, document_path)
        return order, document
```

---

## Document Generation Guidelines

### Template Management

Templates are version-controlled assets stored in `/templates/documents/`.

```python
from pathlib import Path
from docx import Document

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "documents"

class TemplateLoader:
    @staticmethod
    def load_template(plan_type: str) -> Path:
        template_map = {
            "basic": "basic_manual_template.docx",
            "comprehensive": "comprehensive_manual_template.docx",
            "industry_specific": "industry_specific_template.docx"
        }
        
        template_filename = template_map.get(plan_type)
        if not template_filename:
            raise ValueError(f"Unknown plan type: {plan_type}")
        
        template_path = TEMPLATES_DIR / template_filename
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        return template_path
```

### Variable Replacement

Use clear, consistent placeholder syntax and dedicated replacement functions.

```python
from docx import Document
from docx.shared import Inches

def replace_template_variables(doc: Document, replacements: dict[str, str]) -> Document:
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"  # {{company_name}}
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(placeholder, value)
    
    return doc

def insert_company_logo(doc: Document, logo_path: Path, placeholder: str = "{{logo}}") -> Document:
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")
    
    for paragraph in doc.paragraphs:
        if placeholder in paragraph.text:
            paragraph.text = paragraph.text.replace(placeholder, "")
            run = paragraph.add_run()
            run.add_picture(str(logo_path), width=Inches(2.0))
    
    return doc
```

### Document Generation Service

Orchestrate document creation through a dedicated service.

```python
class DocumentGenerationService:
    def __init__(self, file_storage: FileStorageService):
        self.file_storage = file_storage
    
    def generate_manual(self, order: Order) -> Path:
        # Load template
        template_path = TemplateLoader.load_template(order.plan.plan_slug)
        doc = Document(str(template_path))
        
        # Prepare replacements
        replacements = self._build_replacements(order)
        
        # Replace variables
        doc = replace_template_variables(doc, replacements)
        
        # Insert logo if provided
        if order.company.logo_path:
            logo_path = Path(order.company.logo_path)
            doc = insert_company_logo(doc, logo_path)
        
        # Save document
        output_path = self._generate_output_path(order.id)
        doc.save(str(output_path))
        
        return output_path
    
    def _build_replacements(self, order: Order) -> dict[str, str]:
        return {
            "company_name": order.company.company_name,
            "province": order.company.province,
            "naics_codes": ", ".join(order.company.naics_codes),
            "generation_date": datetime.now().strftime("%B %d, %Y")
        }
    
    def _generate_output_path(self, order_id: int) -> Path:
        filename = f"order_{order_id}_{datetime.now().timestamp()}.docx"
        return self.file_storage.get_document_path(filename)
```

---

## File Storage Guidelines

### File Organization

Maintain clear separation between uploaded files and generated documents.

```python
from pathlib import Path
from app.config import settings

class FileStorageService:
    def __init__(self):
        self.uploads_dir = Path(settings.DATA_DIR) / "uploads"
        self.documents_dir = Path(settings.DATA_DIR) / "documents"
        self.previews_dir = self.documents_dir / "previews"
        
        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_logo(self, file_content: bytes, order_id: int, extension: str) -> Path:
        filename = f"{order_id}_logo{extension}"
        logo_path = self.uploads_dir / "logos" / filename
        logo_path.parent.mkdir(exist_ok=True)
        
        logo_path.write_bytes(file_content)
        return logo_path
    
    def get_document_path(self, filename: str) -> Path:
        return self.documents_dir / "generated" / filename
    
    def get_preview_path(self, filename: str) -> Path:
        return self.previews_dir / filename
```

### File Validation

Validate all uploaded files before processing.

```python
from PIL import Image

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg"}
MAX_LOGO_SIZE_MB = 5

def validate_logo_upload(file_content: bytes, filename: str) -> None:
    # Check file size
    size_mb = len(file_content) / (1024 * 1024)
    if size_mb > MAX_LOGO_SIZE_MB:
        raise ValidationError(f"Logo file size exceeds {MAX_LOGO_SIZE_MB}MB limit")
    
    # Check file extension
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_LOGO_EXTENSIONS:
        raise ValidationError(f"Logo file type {extension} not supported. Allowed types: {ALLOWED_LOGO_EXTENSIONS}")
    
    # Validate image integrity
    if extension in {".png", ".jpg", ".jpeg"}:
        try:
            Image.open(io.BytesIO(file_content))
        except Exception:
            raise ValidationError("Uploaded file is not a valid image")
```

---

## Payment Integration Guidelines

### Stripe Integration

Isolate all Stripe operations in a dedicated service.

```python
import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_API_KEY

class PaymentService:
    def create_payment_intent(self, order: Order) -> str:
        if order.total_amount <= 0:
            raise ValueError("Order amount must be greater than zero")
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=order.total_amount,
                currency="cad",
                metadata={
                    "order_id": str(order.id),
                    "user_email": order.user.email
                }
            )
            return intent.client_secret
        except stripe.error.StripeError as e:
            raise PaymentProcessingError(f"Failed to create payment intent: {str(e)}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except stripe.error.SignatureVerificationError:
            raise WebhookValidationError("Invalid webhook signature")
```

### Webhook Handling

Handle Stripe webhooks with idempotency and proper error handling.

```python
from fastapi import Request, HTTPException

@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    payment_service: PaymentService = Depends(get_payment_service),
    order_service: OrderService = Depends(get_order_service)
):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    try:
        event = payment_service.verify_webhook_signature(payload, signature)
    except WebhookValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        order_id = int(payment_intent["metadata"]["order_id"])
        
        # Idempotency check
        order = order_service.get_order(order_id)
        if order.status == OrderStatus.PAID:
            return {"status": "already_processed"}
        
        # Process payment success
        order_service.mark_order_as_paid(order_id)
        order_service.trigger_document_generation(order_id)
    
    return {"status": "received"}
```

---

## Email Service Guidelines

### Email Template Management

Use Jinja2 for email template rendering.

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"

class EmailTemplateRenderer:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(['html'])
        )
    
    def render_order_confirmation(self, order: Order) -> str:
        template = self.env.get_template("order_confirmation.html")
        return template.render(
            company_name=order.company.company_name,
            order_id=order.id,
            total_amount=order.total_amount,
            created_at=order.created_at.strftime("%B %d, %Y")
        )
    
    def render_document_delivery(self, order: Order, download_link: str) -> str:
        template = self.env.get_template("document_delivery.html")
        return template.render(
            company_name=order.company.company_name,
            order_id=order.id,
            download_link=download_link
        )
```

### Email Delivery Service

Handle email sending with retry logic and proper error tracking.

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

class EmailService:
    def __init__(self, email_log_repo: EmailLogRepository):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_log_repo = email_log_repo
    
    def send_document_delivery_email(
        self, 
        recipient_email: str, 
        order: Order, 
        document_path: Path
    ) -> None:
        subject = f"Your OHS Manual is Ready - Order #{order.id}"
        html_body = EmailTemplateRenderer().render_document_delivery(
            order, 
            self._generate_download_link(order.id)
        )
        
        try:
            self._send_email_with_attachment(
                recipient_email, 
                subject, 
                html_body, 
                document_path
            )
            self._log_email_success(order.id, recipient_email, subject)
        except Exception as e:
            self._log_email_failure(order.id, recipient_email, subject, str(e))
            raise EmailDeliveryError(f"Failed to send email: {str(e)}")
    
    def _send_email_with_attachment(
        self, 
        to_email: str, 
        subject: str, 
        html_body: str, 
        attachment_path: Path
    ) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(html_body, "html"))
        
        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="docx")
                attachment.add_header(
                    "Content-Disposition", 
                    "attachment", 
                    filename=attachment_path.name
                )
                msg.attach(attachment)
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
```

---

## Background Tasks with Celery (Phase 2+)

### Task Definition

Define tasks in `app/workers/` with clear naming and error handling.

```python
from app.workers.celery_app import celery_app
from app.services.document_generation_service import DocumentGenerationService

@celery_app.task(bind=True, max_retries=3)
def generate_document_async(self, order_id: int):
    try:
        document_service = get_document_generation_service()
        document_path = document_service.generate_manual(order_id)
        
        # Update order with document path
        order_service = get_order_service()
        order_service.attach_document(order_id, document_path)
        
        # Trigger email delivery
        send_delivery_email_async.delay(order_id)
        
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

@celery_app.task(bind=True, max_retries=3)
def send_delivery_email_async(self, order_id: int):
    try:
        email_service = get_email_service()
        order_service = get_order_service()
        
        order = order_service.get_order(order_id)
        email_service.send_document_delivery_email(order)
        
    except Exception as exc:
        self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
```

### Task Invocation

Call tasks from API endpoints for long-running operations.

```python
@router.post("/orders/{order_id}/generate")
async def trigger_document_generation(
    order_id: int,
    order_service: OrderService = Depends(get_order_service)
):
    order = order_service.get_order(order_id)
    if order.status != OrderStatus.PAID:
        raise HTTPException(status_code=400, detail="Order must be paid before generation")
    
    # Trigger async task
    generate_document_async.delay(order_id)
    
    return {"status": "processing", "order_id": order_id}
```

---

## Logging and Observability

### Structured Logging

Use consistent structured logging throughout the application.

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setFormatter(self._get_formatter())
        self.logger.addHandler(handler)
    
    def _get_formatter(self):
        return JsonFormatter()
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs, exc_info=True)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # Add custom fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", 
                          "pathname", "filename", "module", "exc_info", 
                          "exc_text", "stack_info", "lineno", "funcName", 
                          "created", "msecs", "relativeCreated", "thread", 
                          "threadName", "processName", "process"]:
                log_data[key] = value
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)
```

### Request Logging Middleware

Log all requests and responses with relevant metadata.

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        logger.info(
            "Request received",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host
        )
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_seconds=duration
            )
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                duration_seconds=duration
            )
            raise
```

### Service-Level Logging

Log business operations with context.

```python
class OrderService:
    def __init__(self, order_repo: OrderRepository, logger: StructuredLogger):
        self.order_repo = order_repo
        self.logger = logger
    
    def create_order(self, request: OrderCreateRequest) -> Order:
        self.logger.info(
            "Creating order",
            plan_id=request.plan_id,
            user_email=request.user_email
        )
        
        order = self.order_repo.create(Order.from_request(request))
        
        self.logger.info(
            "Order created successfully",
            order_id=order.id,
            status=order.status.value
        )
        
        return order
    
    def mark_order_as_paid(self, order_id: int) -> Order:
        self.logger.info("Marking order as paid", order_id=order_id)
        
        order = self.order_repo.update_status(order_id, OrderStatus.PAID)
        
        self.logger.info(
            "Order marked as paid",
            order_id=order_id,
            completed_at=order.completed_at
        )
        
        return order
```

---

## Error Handling Strategy

### Exception Hierarchy

Create domain-specific exceptions that inherit from base application exception.

```python
class OHSRemoteException(Exception):
    """Base exception for OHS Remote application"""
    pass

class ValidationError(OHSRemoteException):
    """Validation errors for user input"""
    pass

class OrderNotFoundError(OHSRemoteException):
    """Order does not exist"""
    pass

class DocumentGenerationError(OHSRemoteException):
    """Document generation failures"""
    pass

class PaymentProcessingError(OHSRemoteException):
    """Payment processing failures"""
    pass

class EmailDeliveryError(OHSRemoteException):
    """Email sending failures"""
    pass

class FileStorageError(OHSRemoteException):
    """File storage operations failures"""
    pass
```

### Where to Catch Exceptions

**At the API endpoint level only:**
```python
from app.api.middleware.error_handler import handle_application_errors

@app.exception_handler(OHSRemoteException)
async def ohs_remote_exception_handler(request: Request, exc: OHSRemoteException):
    logger.error("Application error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=400,
        content={"error": {"code": exc.__class__.__name__, "message": str(exc)}}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unexpected error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"}}
    )
```

**Let exceptions bubble from services:**
```python
class DocumentGenerationService:
    def generate_manual(self, order: Order) -> Path:
        # Don't catch here, let it bubble
        template = self._load_template(order.plan.plan_slug)
        document = self._populate_template(template, order)
        return self._save_document(document, order.id)
    
    def _load_template(self, plan_slug: str) -> Path:
        template_path = TEMPLATES_DIR / f"{plan_slug}_template.docx"
        if not template_path.exists():
            raise DocumentGenerationError(f"Template not found for plan: {plan_slug}")
        return template_path
```

---

## Fail Fast Principle

Validate all prerequisites before processing. Fail early with clear error messages, not late with obscure ones.

### Validate Before Processing

Never start processing if you know you'll fail later. Check all requirements at function entry.

**Wrong - Fail late:**
```python
def generate_document(order_id: int):
    order = order_repo.get(order_id)
    template = load_template()
    # ... 50 lines of processing
    
    # Fails here with cryptic error
    logo_path = Path(order.company.logo_path)
    logo = Image.open(logo_path)  # FileNotFoundError if logo_path is None
```

**Correct - Fail fast:**
```python
def generate_document(order_id: int):
    if not order_id:
        raise ValueError("order_id is required for document generation")
    
    order = order_repo.get(order_id)
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    
    if not order.company:
        raise ValidationError(f"Order {order_id} has no associated company")
    
    if not order.company.logo_path:
        raise ValidationError(f"Company logo is required for document generation")
    
    logo_path = Path(order.company.logo_path)
    if not logo_path.exists():
        raise FileStorageError(f"Company logo file not found: {logo_path}")
    
    # Now safe to process
    template = load_template()
    document = populate_template(template, order)
    return save_document(document)
```

### Guard Clauses at Function Entry

Place all validation checks at the top of functions before any processing logic.

```python
def send_document_email(order_id: int, recipient_email: str, document_path: Path):
    # All guards at the top
    if not order_id:
        raise ValueError("order_id is required")
    
    if not recipient_email:
        raise ValueError("recipient_email is required")
    
    if not document_path:
        raise ValueError("document_path is required")
    
    if not document_path.exists():
        raise FileNotFoundError(f"Document file not found: {document_path}")
    
    # Validate email format
    if not validate_email_format(recipient_email):
        raise ValidationError(f"Invalid email format: {recipient_email}")
    
    # Now safe to send
    email_service.send_with_attachment(recipient_email, document_path)
```

### Validation for External Calls

Before making database queries, API calls, or file operations, validate all required parameters.

**Stripe API call:**
```python
def create_payment_intent(order_id: int, amount: int):
    if not order_id:
        raise ValueError("order_id is required for payment intent")
    
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    
    if not settings.STRIPE_API_KEY:
        raise ConfigurationError("STRIPE_API_KEY is not configured")
    
    # Now safe to call Stripe
    intent = stripe.PaymentIntent.create(amount=amount, currency="cad")
```

**File operations:**
```python
def resize_logo(logo_path: Path, max_width: int, max_height: int) -> Path:
    if not logo_path:
        raise ValueError("logo_path is required")
    
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")
    
    if max_width <= 0 or max_height <= 0:
        raise ValueError("max_width and max_height must be positive integers")
    
    # Now safe to process
    image = Image.open(logo_path)
    resized = image.resize((max_width, max_height))
    return save_resized_image(resized)
```

---

## Configuration and Environment Variables

### Never Use Default Values

Configuration must be explicit. If a required value is missing, fail immediately at startup.

**Bad:**
```python
DATABASE_URL = os.getenv("DATABASE_URL", "mysql://localhost/ohs_remote")  # Silent failure
```

**Good:**
```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
```

**Best with Pydantic:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # No default, will fail if missing
    smtp_host: str
    smtp_port: int
    stripe_api_key: str
    stripe_webhook_secret: str
    
    class Config:
        env_file = ".env"

settings = Settings()  # Fails immediately if required vars are missing
```

### Environment-Specific Configuration

Separate configuration by environment.

```python
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    environment: Environment
    database_url: str
    debug: bool = False
    
    # Storage
    data_dir: str
    use_s3: bool = False
    s3_bucket_name: str | None = None
    
    # Email
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    
    # Stripe
    stripe_api_key: str
    stripe_webhook_secret: str
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Database Migration with Alembic

### Creating New Migrations

Always use Alembic CLI to create migration files. Never create them manually.

**Process:**
```bash
# From project root
alembic revision -m "add order_status table"

# Edit the generated file in alembic/versions/
# Add your upgrade and downgrade logic
```

### Migration Best Practices

**Always include both upgrade and downgrade:**
```python
def upgrade():
    op.create_table(
        'order_status',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    op.drop_table('order_status')
```

**Test migrations before committing:**
```bash
# Apply migration
alembic upgrade head

# Verify schema changes
# Check application functionality

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

---

## Testing Guidelines

### Unit Tests

Test individual functions and methods in isolation.

```python
import pytest
from app.services.validation_service import ValidationService

class TestValidationService:
    def test_validate_naics_code_valid(self):
        service = ValidationService()
        result = service.validate_naics_code("123456")
        assert result is True
    
    def test_validate_naics_code_invalid_length(self):
        service = ValidationService()
        with pytest.raises(ValidationError, match="NAICS code must be exactly 6 digits"):
            service.validate_naics_code("12345")
    
    def test_validate_naics_code_non_numeric(self):
        service = ValidationService()
        with pytest.raises(ValidationError, match="NAICS code must contain only digits"):
            service.validate_naics_code("12345a")
```

### Integration Tests

Test interactions between services and repositories.

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database.base import Base
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()

def test_create_order_integration(test_db):
    order_repo = OrderRepository(test_db)
    order_service = OrderService(order_repo)
    
    request = OrderCreateRequest(
        plan_id="basic",
        user_email="test@example.com",
        company_name="Test Company"
    )
    
    order = order_service.create_order(request)
    
    assert order.id is not None
    assert order.status == OrderStatus.PENDING
    assert order.company.company_name == "Test Company"
```

### API Tests

Test endpoints with httpx test client.

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_order_endpoint():
    response = client.post("/api/v1/orders", json={
        "plan_id": "basic",
        "user_email": "test@example.com",
        "company_name": "Test Company"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "order_id" in data
    assert data["status"] == "pending"

def test_create_order_invalid_email():
    response = client.post("/api/v1/orders", json={
        "plan_id": "basic",
        "user_email": "invalid-email",
        "company_name": "Test Company"
    })
    
    assert response.status_code == 422
    assert "error" in response.json()
```

---

## Import Organization

Organize imports in three groups separated by blank lines:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.order import Order, OrderStatus
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services.order_service import OrderService
```

### Import Style

**Use absolute imports:**
```python
from app.services.order_service import OrderService
```

**Not relative imports:**
```python
from ..services.order_service import OrderService  # Avoid
```

**Import specific items:**
```python
from app.models.order import Order, OrderStatus
```

**Not entire modules unless necessary:**
```python
import app.models  # Avoid unless you need the namespace
```

---

## Version Control

### Commit Guidelines

Commit changes logically, one change per commit. Use clear, descriptive commit messages.

**Good commit messages:**
- `Add OrderStatus enum for order state management`
- `Implement document generation service with template processing`
- `Add validation for NAICS code format`
- `Refactor file storage service to support S3`

**Bad commit messages:**
- `Updates` (too vague)
- `Fixed stuff` (not descriptive)
- `Multiple changes to orders and documents` (should be separate commits)

**Never bulk commit.** Each logical change should be its own commit.

### Branch Naming

Use descriptive branch names that indicate the type of change:

```
feature/add-document-preview-generation
bugfix/fix-logo-upload-validation
refactor/extract-email-service
chore/update-dependencies
```

---

## Code Review Checklist

Before submitting code, verify:

- [ ] No dictionaries used where Pydantic models would be better
- [ ] No result dictionaries with success/error flags
- [ ] All functions have a single, clear responsibility
- [ ] Function names are business-level and self-explanatory
- [ ] No comments or docstrings (code is self-documenting)
- [ ] Enums used for fixed value sets
- [ ] Pydantic models for all request/response validation
- [ ] Type hints on all function signatures
- [ ] Files are focused and understandable in under 20 minutes
- [ ] Commits are logical and atomic
- [ ] Modern Python features used (no deprecated patterns)
- [ ] All exceptions are domain-specific and handled at endpoint level
- [ ] Structured logging used consistently
- [ ] Dependencies are injected via FastAPI's Depends
- [ ] Imports are organized (stdlib, third-party, local)
- [ ] No default values for required configuration
- [ ] All input validated before processing (fail fast)
- [ ] Database queries optimized (no N+1 problems)
- [ ] File operations validated before execution
- [ ] Tests written for new functionality

---

## Summary

Clean, maintainable code is the foundation of a successful project. When in doubt:

1. Split complex functions into smaller, focused ones
2. Use Pydantic models instead of dictionaries
3. Make behavior explicit through clear naming
4. Let exceptions handle errors naturally
5. Validate all inputs before processing
6. Think about future maintainability
7. Fail fast with clear error messages
8. Log structured data consistently
9. Inject dependencies rather than instantiating globally
10. Test thoroughly at all levels

Code should be written to be read by humans first, executed by computers second.