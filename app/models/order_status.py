from enum import Enum

from sqlalchemy import Column, Integer, String, CHAR, ForeignKey
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
    order_status = Column(String(50), nullable=False, default="draft")
    currency = Column(CHAR(3), nullable=False, default="CAD")
    payment_provider = Column(String(35), nullable=True)
    payment_status = Column(String(50), nullable=False, default="pending")
    stripe_checkout_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="order_status")