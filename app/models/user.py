from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, CHAR
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(Enum):
    ADMIN = "admin"
    CONTENT_MANAGER = "content_manager"
    SUPPORT = "support"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    company_id = Column(Integer, ForeignKey("company.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    otp_token = Column(CHAR(6), nullable=True)
    otp_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="users")
    orders = relationship("Order", back_populates="user")
    system_logs = relationship("SystemLog", back_populates="user")