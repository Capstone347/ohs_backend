from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("company.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    jurisdiction = Column(String(100), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    is_industry_specific = Column(Boolean, nullable=False, default=False)
    admin_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="orders")
    plan = relationship("Plan", back_populates="orders")
    company = relationship("Company", back_populates="orders")
    documents = relationship("Document", back_populates="order")
    company_logos = relationship("CompanyLogo", back_populates="order")
    email_logs = relationship("EmailLog", back_populates="order")
    system_logs = relationship("SystemLog", back_populates="order")
    legal_acknowledgments = relationship("LegalAcknowledgement", back_populates="order")
    naics_user_content = relationship("NAICSUserContent", back_populates="order")
    order_status = relationship("OrderStatus", back_populates="order", uselist=False)
    industry_intake_response = relationship("IndustryIntakeResponse", back_populates="order", uselist=False)
    sjp_generation_jobs = relationship("SjpGenerationJob", back_populates="order")
