from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class SjpContentStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SjpContent(Base):
    __tablename__ = "sjp_contents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    toc_entry_id = Column(
        Integer,
        ForeignKey("sjp_toc_entries.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )
    task_description = Column(Text, nullable=False)
    required_ppe = Column(JSON, nullable=False)
    step_by_step_instructions = Column(JSON, nullable=False)
    identified_hazards = Column(JSON, nullable=False)
    control_measures = Column(JSON, nullable=False)
    training_requirements = Column(JSON, nullable=False)
    emergency_procedures = Column(Text, nullable=False)
    legislative_references = Column(Text, nullable=True)
    raw_ai_response = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default=SjpContentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)

    toc_entry = relationship("SjpTocEntry", back_populates="content")

