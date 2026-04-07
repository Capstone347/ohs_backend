from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class AdminRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    SUPPORT = "support"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=AdminRole.MANAGER.value)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    last_login = Column(DateTime, nullable=True)
