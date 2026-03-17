from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class AuthOtpRequest(Base):
    __tablename__ = "auth_otp_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    attempt_count = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    request_ip = Column(String(64), nullable=True, index=True)
    lockout_until = Column(DateTime, nullable=True)

