from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan, PlanSlug, PlanName
from app.repositories.base_repository import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, db: Session):
        super().__init__(Plan, db)

    def get_by_slug(self, slug: PlanSlug) -> Plan | None:
        if not slug:
            raise ValueError("slug is required")
        
        return self.db.query(Plan).filter(Plan.slug == slug).first()

    def get_by_slug_or_fail(self, slug: PlanSlug) -> Plan:
        plan = self.get_by_slug(slug)
        if not plan:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"Plan with slug {slug} not found")
        return plan

    def get_by_name(self, name: PlanName) -> Plan | None:
        if not name:
            raise ValueError("name is required")
        
        return self.db.query(Plan).filter(Plan.name == name).first()

    def get_all_plans(self) -> list[Plan]:
        return self.db.query(Plan).order_by(Plan.base_price.asc()).all()

    def get_by_id_with_orders(self, plan_id: int) -> Plan | None:
        if not plan_id:
            raise ValueError("plan_id is required")
        
        return (
            self.db.query(Plan)
            .options(joinedload(Plan.orders))
            .filter(Plan.id == plan_id)
            .first()
        )

    def create_plan(
        self,
        slug: PlanSlug,
        name: PlanName,
        base_price: float,
        description: str | None = None
    ) -> Plan:
        if not slug:
            raise ValueError("slug is required")
        
        if not name:
            raise ValueError("name is required")
        
        if base_price < 0:
            raise ValueError("base_price cannot be negative")
        
        from app.repositories.base_repository import DuplicateRecordError
        
        if self.get_by_slug(slug):
            raise DuplicateRecordError(f"Plan with slug {slug} already exists")
        
        plan = Plan(
            slug=slug,
            name=name,
            base_price=base_price,
            description=description
        )
        return self.create(plan)

    def update_base_price(self, plan_id: int, new_price: float) -> Plan:
        if not plan_id:
            raise ValueError("plan_id is required")
        
        if new_price < 0:
            raise ValueError("new_price cannot be negative")
        
        plan = self.get_by_id_or_fail(plan_id)
        plan.base_price = new_price
        return self.update(plan)

    def update_description(self, plan_id: int, description: str) -> Plan:
        if not plan_id:
            raise ValueError("plan_id is required")
        
        plan = self.get_by_id_or_fail(plan_id)
        plan.description = description
        return self.update(plan)

    def slug_exists(self, slug: PlanSlug) -> bool:
        if not slug:
            raise ValueError("slug is required")
        
        return self.get_by_slug(slug) is not None

    def get_basic_plan(self) -> Plan | None:
        return self.get_by_slug(PlanSlug.BASIC)

    def get_comprehensive_plan(self) -> Plan | None:
        return self.get_by_slug(PlanSlug.COMPREHENSIVE)

    def get_plans_by_price_range(self, min_price: float, max_price: float) -> list[Plan]:
        if min_price < 0:
            raise ValueError("min_price cannot be negative")
        
        if max_price < 0:
            raise ValueError("max_price cannot be negative")
        
        if min_price > max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        
        return (
            self.db.query(Plan)
            .filter(Plan.base_price >= min_price, Plan.base_price <= max_price)
            .order_by(Plan.base_price.asc())
            .all()
        )
