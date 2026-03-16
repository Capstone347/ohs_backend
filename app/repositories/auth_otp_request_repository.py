from datetime import datetime

from sqlalchemy.orm import Session

from app.models.auth_otp_request import AuthOtpRequest
from app.repositories.base_repository import BaseRepository


class AuthOtpRequestRepository(BaseRepository[AuthOtpRequest]):
    def __init__(self, db: Session):
        super().__init__(AuthOtpRequest, db)

    def get_latest_by_email(self, email: str) -> AuthOtpRequest | None:
        if not email:
            raise ValueError("email is required")

        return (
            self.db.query(AuthOtpRequest)
            .filter(AuthOtpRequest.email == email)
            .order_by(AuthOtpRequest.id.desc())
            .first()
        )

    def count_recent_by_ip(self, request_ip: str, window_start: datetime) -> int:
        if not request_ip:
            raise ValueError("request_ip is required")

        if not window_start:
            raise ValueError("window_start is required")

        return int(
            self.db.query(AuthOtpRequest)
            .filter(
                AuthOtpRequest.request_ip == request_ip,
                AuthOtpRequest.last_sent_at >= window_start,
            )
            .count()
        )

    def upsert_otp_request(
        self,
        email: str,
        otp_hash: str,
        expires_at: datetime,
        sent_at: datetime,
        request_ip: str | None,
        attempt_count: int,
    ) -> AuthOtpRequest:
        if not email:
            raise ValueError("email is required")

        if not otp_hash:
            raise ValueError("otp_hash is required")

        if not expires_at:
            raise ValueError("expires_at is required")

        if not sent_at:
            raise ValueError("sent_at is required")

        if attempt_count < 0:
            raise ValueError("attempt_count must be non-negative")

        existing = self.get_latest_by_email(email)

        if not existing:
            entity = AuthOtpRequest(
                email=email,
                otp_hash=otp_hash,
                expires_at=expires_at,
                created_at=sent_at,
                attempt_count=attempt_count,
                last_sent_at=sent_at,
                request_ip=request_ip,
                lockout_until=None,
            )
            return self.create(entity)

        existing.otp_hash = otp_hash
        existing.expires_at = expires_at
        existing.last_sent_at = sent_at
        existing.request_ip = request_ip
        existing.attempt_count = attempt_count
        existing.lockout_until = None
        return self.update(existing)

    def set_lockout(
        self,
        email: str,
        lockout_until: datetime,
        request_ip: str | None,
    ) -> AuthOtpRequest:
        if not email:
            raise ValueError("email is required")

        if not lockout_until:
            raise ValueError("lockout_until is required")

        existing = self.get_latest_by_email(email)

        if not existing:
            entity = AuthOtpRequest(
                email=email,
                otp_hash="lockout",
                expires_at=lockout_until,
                created_at=lockout_until,
                attempt_count=0,
                last_sent_at=lockout_until,
                request_ip=request_ip,
                lockout_until=lockout_until,
            )
            return self.create(entity)

        existing.lockout_until = lockout_until
        existing.request_ip = request_ip
        return self.update(existing)

