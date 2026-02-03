from fastapi import APIRouter, Depends, Request, HTTPException, status
import json

from app.api.dependencies import (
    get_order_status_repository,
    get_payment_service,
    get_order_repository,
    get_email_template_renderer,
    get_email_service,
    get_document_repository,
    get_document_service,
)
from app.repositories.order_status_repository import OrderStatusRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.schemas.payment import StripeWebhookEvent, StripeWebhookEventType
from app.schemas.email import DocumentDeliveryContext
from app.services.payment_service import PaymentService
from app.services.email_template_renderer import EmailTemplateRenderer
from app.services.email_service import EmailService
from app.config import settings

router = APIRouter()


@router.post(
    "/webhooks/payment-confirmation",
    status_code=status.HTTP_200_OK,
)
async def handle_payment_webhook(
    request: Request,
    order_status_repo: OrderStatusRepository = Depends(get_order_status_repository),
    payment_service: PaymentService = Depends(get_payment_service),
    order_repo: OrderRepository = Depends(get_order_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    document_service: DocumentService = Depends(get_document_service),
    renderer: EmailTemplateRenderer = Depends(get_email_template_renderer),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    signature = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    body = await request.body()
    
    if not body:
        raise HTTPException(status_code=400, detail="Request body is required")

    event: StripeWebhookEvent

    if signature and settings.stripe_webhook_secret:
        try:
            event = payment_service.verify_webhook_signature(body, signature)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process webhook: {str(e)}")
    else:
        try:
            payload = json.loads(body.decode("utf-8"))
            event = StripeWebhookEvent(**payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {str(e)}")

    if event.event_type != StripeWebhookEventType.PAYMENT_INTENT_SUCCEEDED:
        return {"status": "ignored", "reason": "not a succeeded event"}

    metadata = event.metadata or {}
    order_id_str = metadata.get("order_id")
    
    if not order_id_str:
        raise HTTPException(status_code=400, detail="order_id missing from metadata")

    try:
        order_id = int(order_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order_id in metadata")
    
    if order_id <= 0:
        raise HTTPException(status_code=400, detail="order_id must be greater than 0")

    order_status_repo.mark_as_paid(order_id, payment_provider="stripe")

    try:
        order = order_repo.get_by_id_with_relations(order_id)
    except Exception:
        return {"status": "ok", "warning": "Payment marked but delivery failed"}

    company_name = getattr(order.company, "name", "") if order and getattr(order, "company", None) else ""
    recipient = order.user.email if order and getattr(order, "user", None) else ""
    
    if recipient:
        # Check if document exists, if not generate it
        documents = document_repo.get_documents_by_order_id(order_id)
        
        if not documents:
            # Generate document after payment
            try:
                document = document_service.generate_document_for_order(order_id)
                documents = [document]
            except Exception as e:
                return {"status": "ok", "warning": f"Payment marked but document generation failed: {str(e)}"}
        
        access_token = documents[0].access_token if documents else ""
        document_id = documents[0].document_id if documents else order_id
        
        download_link = f"{settings.app_base_url}/api/v1/documents/{document_id}/download"
        if access_token:
            download_link += f"?token={access_token}"
        
        context_model = DocumentDeliveryContext(
            order_id=order_id,
            company_name=company_name or "",
            download_link=download_link,
            document_name=f"order_{order_id}_document.pdf",
        )
        html_body = renderer.render_document_delivery(context_model)
        email_service.send_email(order_id, recipient, "Your documents are ready", html_body)

    return {"status": "ok"}
