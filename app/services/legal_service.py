from datetime import datetime, timezone

from app.models.legal_acknowledgment import LegalAcknowledgement
from app.models.plan import Plan, PlanSlug
from app.repositories.legal_acknowledgment_repository import LegalAcknowledgmentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.plan_repository import PlanRepository
from app.services.exceptions import (
    ServiceException,
    FileNotFoundServiceException,
)


LEGAL_DISCLAIMERS_BASE = {
    "basic": {
        "AB": "Alberta Basic OHS Manual Legal Disclaimer...",
        "BC": "British Columbia Basic OHS Manual Legal Disclaimer...",
        "MB": "Manitoba Basic OHS Manual Legal Disclaimer...",
        "NB": "New Brunswick Basic OHS Manual Legal Disclaimer...",
        "NL": "Newfoundland and Labrador Basic OHS Manual Legal Disclaimer...",
        "NS": "Nova Scotia Basic OHS Manual Legal Disclaimer...",
        "NT": "Northwest Territories Basic OHS Manual Legal Disclaimer...",
        "NU": "Nunavut Basic OHS Manual Legal Disclaimer...",
        "ON": "Ontario Basic OHS Manual Legal Disclaimer...",
        "PE": "Prince Edward Island Basic OHS Manual Legal Disclaimer...",
        "QC": "Quebec Basic OHS Manual Legal Disclaimer...",
        "SK": "Saskatchewan Basic OHS Manual Legal Disclaimer...",
        "YT": "Yukon Basic OHS Manual Legal Disclaimer...",
    },
    "comprehensive": {
        "AB": "Alberta Comprehensive OHS Manual Legal Disclaimer...",
        "BC": "British Columbia Comprehensive OHS Manual Legal Disclaimer...",
        "MB": "Manitoba Comprehensive OHS Manual Legal Disclaimer...",
        "NB": "New Brunswick Comprehensive OHS Manual Legal Disclaimer...",
        "NL": "Newfoundland and Labrador Comprehensive OHS Manual Legal Disclaimer...",
        "NS": "Nova Scotia Comprehensive OHS Manual Legal Disclaimer...",
        "NT": "Northwest Territories Comprehensive OHS Manual Legal Disclaimer...",
        "NU": "Nunavut Comprehensive OHS Manual Legal Disclaimer...",
        "ON": "Ontario Comprehensive OHS Manual Legal Disclaimer...",
        "PE": "Prince Edward Island Comprehensive OHS Manual Legal Disclaimer...",
        "QC": "Quebec Comprehensive OHS Manual Legal Disclaimer...",
        "SK": "Saskatchewan Comprehensive OHS Manual Legal Disclaimer...",
        "YT": "Yukon Comprehensive OHS Manual Legal Disclaimer...",
    },
}


class LegalService:
    def __init__(
        self,
        legal_acknowledgment_repository: LegalAcknowledgmentRepository,
        order_repository: OrderRepository,
        plan_repository: PlanRepository,
    ):
        self.legal_acknowledgment_repository = legal_acknowledgment_repository
        self.order_repository = order_repository
        self.plan_repository = plan_repository

    def get_legal_disclaimer(self, plan_id: int, jurisdiction: str) -> str:
        if not plan_id:
            raise ValueError("plan_id is required")
        
        if not jurisdiction:
            raise ValueError("jurisdiction is required")
        
        plan = self.plan_repository.get_by_id_or_fail(plan_id)
        
        if plan.slug not in LEGAL_DISCLAIMERS_BASE:
            raise FileNotFoundServiceException(f"No legal disclaimers available for plan: {plan.slug}")
        
        jurisdiction_disclaimers = LEGAL_DISCLAIMERS_BASE[plan.slug]
        
        if jurisdiction not in jurisdiction_disclaimers:
            raise FileNotFoundServiceException(f"No legal disclaimer available for jurisdiction: {jurisdiction}")
        
        return jurisdiction_disclaimers[jurisdiction]

    def record_acknowledgment(
        self,
        order_id: int,
        jurisdiction: str,
        content: str,
        version: int = 1
    ) -> LegalAcknowledgement:
        if not order_id:
            raise ValueError("order_id is required for acknowledgment")
        
        if not jurisdiction:
            raise ValueError("jurisdiction is required for acknowledgment")
        
        if not content:
            raise ValueError("content is required for acknowledgment")
        
        order = self.order_repository.get_by_id_or_fail(order_id)
        
        existing_acknowledgment = self.legal_acknowledgment_repository.get_by_order_id(order_id)
        if existing_acknowledgment:
            raise ServiceException(f"Legal acknowledgment already exists for order {order_id}")
        
        acknowledgment = self.legal_acknowledgment_repository.create_acknowledgment(
            order_id=order_id,
            jurisdiction=jurisdiction,
            content=content,
            version=version,
            effective_date=datetime.now(timezone.utc).date()
        )
        
        return acknowledgment

    def get_acknowledgment_by_order(self, order_id: int) -> LegalAcknowledgement:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.legal_acknowledgment_repository.get_by_order_id_or_fail(order_id)
