from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from app.config import Settings
from app.repositories.auth_otp_request_repository import AuthOtpRequestRepository
from app.repositories.user_repository import UserRepository
from app.schemas.email import AuthOtpContext
from app.services.email_service import EmailService
from app.services.email_template_renderer import EmailTemplateRenderer


class AuthService:
    def __init__(
        self,
        auth_otp_request_repo: AuthOtpRequestRepository,
        user_repo: UserRepository,
        email_service: EmailService,
        email_template_renderer: EmailTemplateRenderer,
        settings: Settings,
    ):
        self.auth_otp_request_repo = auth_otp_request_repo
        self.user_repo = user_repo
        self.email_service = email_service
        self.email_template_renderer = email_template_renderer
        self.settings = settings

    def request_otp(self, email: str, request_ip: str | None) -> None:
        if not email:
            raise ValueError("email is required")

        now = datetime.now(timezone.utc)
        normalized_email = email.strip().lower()
        otp_request = self.auth_otp_request_repo.get_latest_by_email(normalized_email)

        lockout_until = self._to_utc(otp_request.lockout_until) if otp_request and otp_request.lockout_until else None
        if lockout_until and now < lockout_until:
            return

        window_start = now - timedelta(minutes=self.settings.auth_otp_rate_limit_window_minutes)

        if request_ip:
            ip_count = self.auth_otp_request_repo.count_recent_by_ip(request_ip, window_start)
            if ip_count >= self.settings.auth_otp_ip_rate_limit_count:
                self._apply_lockout(normalized_email, request_ip, now)
                return

        if otp_request and otp_request.last_sent_at:
            cooldown_elapsed_seconds = (now - self._to_utc(otp_request.last_sent_at)).total_seconds()
            if cooldown_elapsed_seconds < self.settings.auth_otp_resend_cooldown_seconds:
                return

        next_attempt_count = self._get_next_attempt_count(
            otp_request_created_at=otp_request.created_at if otp_request else None,
            otp_request_attempt_count=otp_request.attempt_count if otp_request else 0,
            window_start=window_start,
        )

        if next_attempt_count >= self.settings.auth_otp_email_rate_limit_count:
            self._apply_lockout(normalized_email, request_ip, now)
            return

        otp_code = self._generate_otp_code()
        otp_hash = self._hash_otp_code(otp_code)
        expires_at = now + timedelta(minutes=self.settings.auth_otp_ttl_minutes)

        self.auth_otp_request_repo.upsert_otp_request(
            email=normalized_email,
            otp_hash=otp_hash,
            expires_at=expires_at,
            sent_at=now,
            request_ip=request_ip,
            attempt_count=next_attempt_count,
        )

        user = self.user_repo.get_by_email(normalized_email)
        if not user:
            return

        html_body = self.email_template_renderer.render_auth_otp(
            AuthOtpContext(
                otp_code=otp_code,
                expires_in_minutes=self.settings.auth_otp_ttl_minutes,
                recipient_email=normalized_email,
            )
        )
        try:
            self.email_service.send_transactional_email(
                recipient_email=normalized_email,
                subject="Your OHS Remote verification code",
                html_body=html_body,
            )
        except Exception:
            return

    def _get_next_attempt_count(
        self,
        otp_request_created_at: datetime | None,
        otp_request_attempt_count: int,
        window_start: datetime,
    ) -> int:
        if not otp_request_created_at:
            return 0

        if self._to_utc(otp_request_created_at) < window_start:
            return 0

        return otp_request_attempt_count + 1

    def _apply_lockout(self, email: str, request_ip: str | None, now: datetime) -> None:
        lockout_until = now + timedelta(minutes=self.settings.auth_otp_lockout_minutes)
        self.auth_otp_request_repo.set_lockout(
            email=email,
            lockout_until=lockout_until,
            request_ip=request_ip,
        )

    def _generate_otp_code(self) -> str:
        otp_number = secrets.randbelow(1000000)
        return f"{otp_number:06d}"

    def _hash_otp_code(self, otp_code: str) -> str:
        secret_key_bytes = self.settings.secret_key.encode("utf-8")
        otp_code_bytes = otp_code.encode("utf-8")
        return hmac.new(secret_key_bytes, otp_code_bytes, hashlib.sha256).hexdigest()

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


