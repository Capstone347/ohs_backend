from fastapi import APIRouter

from app.api.v1.endpoints import health, payments, webhooks, documents, legal, orders, industry_intake

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(legal.router, tags=["legal"])
api_router.include_router(payments.router, tags=["payments"])
api_router.include_router(webhooks.router, tags=["webhooks"])
api_router.include_router(industry_intake.router, prefix="/industry", tags=["industry-intake"])
