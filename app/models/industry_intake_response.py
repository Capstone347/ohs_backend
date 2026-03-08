from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class IndustryIntakeResponse(Base):
    __tablename__ = "industry_intake_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="NO ACTION", onupdate="NO ACTION"),
        nullable=False,
        unique=True,
        index=True,
    )
    answers = Column(JSON, nullable=False, default=dict)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    order = relationship("Order", back_populates="industry_intake_response")
