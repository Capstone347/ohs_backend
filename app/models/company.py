from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "company"

    id = Column(Integer, primary_key=True, autoincrement=True)
    logo_id = Column(Integer, nullable=True)
    name = Column(String(45), nullable=True)

    users = relationship("User", back_populates="company")
    orders = relationship("Order", back_populates="company")
    logo = relationship(
        "CompanyLogo", 
        foreign_keys=[logo_id],
        primaryjoin="Company.logo_id == CompanyLogo.id" 
    )