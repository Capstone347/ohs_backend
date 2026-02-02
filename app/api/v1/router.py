from fastapi import APIRouter

from app.api.v1.endpoints import health, payments, webhooks

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(payments.router, tags=["payments"]) 
api_router.include_router(webhooks.router, tags=["webhooks"]) 
