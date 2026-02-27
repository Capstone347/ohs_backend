from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class IndustryProfile(Base):
    __tablename__ = "industry_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, unique=True, index=True)
    province = Column(String(50), nullable=True)
    business_description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    company = relationship("Company", back_populates="industry_profile")
    naics_codes = relationship(
        "IndustryNAICSCode",
        back_populates="industry_profile",
        cascade="all, delete-orphan",
        order_by="IndustryNAICSCode.position",
    )