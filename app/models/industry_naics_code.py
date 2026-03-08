from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class IndustryNAICSCode(Base):
    __tablename__ = "industry_naics_codes"
    __table_args__ = (
        UniqueConstraint("industry_profile_id", "code", name="uq_industry_naics_profile_code"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry_profile_id = Column(Integer, ForeignKey("industry_profiles.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    industry_profile = relationship("IndustryProfile", back_populates="naics_codes")