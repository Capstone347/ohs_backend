from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SjpTocEntry(Base):
    __tablename__ = "sjp_toc_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        Integer,
        ForeignKey("sjp_generation_jobs.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    job = relationship("SjpGenerationJob", back_populates="toc_entries")
    content = relationship("SjpContent", back_populates="toc_entry", uselist=False, cascade="all, delete-orphan")

