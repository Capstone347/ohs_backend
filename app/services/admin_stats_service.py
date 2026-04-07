from decimal import Decimal

from app.models.order_status import OrderStatusEnum
from app.repositories.order_repository import OrderRepository


class AdminStatsService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def get_dashboard_stats(self) -> dict:
        stats = self.order_repo.get_revenue_stats()

        pending_review_count = stats["orders_by_status"].get(
            OrderStatusEnum.REVIEW_PENDING.value, 0
        )

        return {
            "total_revenue": Decimal(str(stats["total_revenue"])),
            "total_orders": stats["total_orders"],
            "orders_by_status": stats["orders_by_status"],
            "orders_by_plan": stats["orders_by_plan"],
            "revenue_by_plan": {
                k: Decimal(str(v)) for k, v in stats["revenue_by_plan"].items()
            },
            "pending_review_count": pending_review_count,
        }
