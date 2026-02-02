from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class EmailStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    recipient_email = Column(String(255), ForeignKey("users.email", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    status = Column(SQLEnum(EmailStatus), nullable=False, default=EmailStatus.PENDING)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    failure_reason = Column(Text, nullable=True)

    order = relationship("Order", back_populates="email_logs")
    user = relationship("User", foreign_keys=[recipient_email])