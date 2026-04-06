from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class SjpGenerationStatus(Enum):
    PENDING = "pending"
    GENERATING_TOC = "generating_toc"
    GENERATING_SJPS = "generating_sjps"
    COMPLETED = "completed"
    FAILED = "failed"


class SjpGenerationJob(Base):
    __tablename__ = "sjp_generation_jobs"

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_sjp_generation_jobs_idempotency_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )
    province = Column(String(50), nullable=False)
    naics_codes = Column(JSON, nullable=False)
    business_description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=SjpGenerationStatus.PENDING.value)
    toc_generated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="sjp_generation_jobs")
