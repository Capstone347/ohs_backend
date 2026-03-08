from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.plan_repository import PlanRepository
from app.schemas.plan import PlanListResponse, PlanResponse

router = APIRouter()


def get_plan_repository(db: Session = Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)


@router.get("/plans", response_model=PlanListResponse)
async def get_all_plans(
    plan_repo: PlanRepository = Depends(get_plan_repository)
):
    plans = plan_repo.get_all_plans()
    
    return PlanListResponse(
        plans=[PlanResponse.model_validate(plan) for plan in plans],
        total=len(plans)
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_by_id(
    plan_id: int,
    plan_repo: PlanRepository = Depends(get_plan_repository)
):
    plan = plan_repo.get_by_id_or_fail(plan_id)
    return PlanResponse.model_validate(plan)
