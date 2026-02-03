from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, BigInteger, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class LogLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    log_level = Column(String(50), nullable=False, default="info")
    source = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    log_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="system_logs")
    order = relationship("Order", back_populates="system_logs")