from enum import Enum

from sqlalchemy import Column, Integer, String, CHAR, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class OrderStatusEnum(Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    REVIEW_PENDING = "review_pending"
    AVAILABLE = "available"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(Base):
    __tablename__ = "order_status"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="NO ACTION", onupdate="NO ACTION"), primary_key=True)
    order_status = Column(SQLEnum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.DRAFT)
    currency = Column(CHAR(3), nullable=False, default="CAD")
    payment_provider = Column(String(35), nullable=True)
    payment_status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)

    order = relationship("Order", back_populates="order_status")