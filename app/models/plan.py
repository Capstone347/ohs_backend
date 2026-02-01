from enum import Enum
from sqlalchemy import Column, Integer, String, Text, Numeric, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base


class PlanSlug(str, Enum):
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"


class PlanName(str, Enum):
    BASIC = "Basic"
    COMPREHENSIVE = "Comprehensive"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(SQLEnum(PlanSlug), nullable=False, unique=True)
    name = Column(SQLEnum(PlanName), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)

    orders = relationship("Order", back_populates="plan")