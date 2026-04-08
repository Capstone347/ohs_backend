from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class LlmUsageStage(Enum):
    TOC = "toc"
    SJP_CONTENT = "sjp_content"


class LlmUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        Integer,
        ForeignKey("sjp_generation_jobs.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )
    toc_entry_id = Column(
        Integer,
        ForeignKey("sjp_toc_entries.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=True,
        index=True,
    )
    stage = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    job = relationship("SjpGenerationJob", back_populates="llm_usage_logs")
    toc_entry = relationship("SjpTocEntry", back_populates="llm_usage_logs")

