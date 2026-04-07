from fastapi import APIRouter

from app.api.v1.endpoints import admin, admin_auth, auth, documents, health, industry_intake, legal, orders, payments, plans, webhooks

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(plans.router, tags=["plans"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(legal.router, tags=["legal"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"]) 
api_router.include_router(webhooks.router, tags=["webhooks"])
api_router.include_router(industry_intake.router, prefix="/industry", tags=["industry-intake"])
api_router.include_router(admin_auth.router, prefix="/admin", tags=["admin-auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
