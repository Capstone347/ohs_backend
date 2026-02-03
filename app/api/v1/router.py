from fastapi import APIRouter

from app.api.v1.endpoints import health, documents, legal, orders

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(legal.router, tags=["legal"])
