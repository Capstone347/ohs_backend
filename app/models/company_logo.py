from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class CompanyLogo(Base):
    __tablename__ = "company_logos"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    order = relationship("Order", back_populates="company_logos")
    companies = relationship(
        "Company", 
        primaryjoin="Company.logo_id == foreign(CompanyLogo.id)"  
    )