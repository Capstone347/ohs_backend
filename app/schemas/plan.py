from decimal import Decimal

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    base_price: Decimal = Field(..., description="Base price in CAD")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "slug": "basic",
                "name": "Basic",
                "description": "Essential health and safety manual for small businesses",
                "base_price": 49.99
            }
        }
    }


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
    total: int
