import base64
import binascii
import json
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

    def verify_otp(self, email: str, otp_code: str) -> dict[str, str | dict[str, int | str]]:
        if not email:
            raise ValueError("email is required")

        if not otp_code:
            raise ValueError("otp_code is required")

        now = datetime.now(timezone.utc)
        normalized_email = email.strip().lower()
        normalized_otp = otp_code.strip()

        otp_request = self.auth_otp_request_repo.get_latest_by_email(normalized_email)
        if not otp_request:
            raise ValueError("invalid authentication")

        if otp_request.lockout_until and now < self._to_utc(otp_request.lockout_until):
            raise ValueError("invalid authentication")

        if now > self._to_utc(otp_request.expires_at):
            raise ValueError("invalid authentication")

        current_attempt_count = int(otp_request.attempt_count or 0)
        if current_attempt_count >= self.settings.auth_otp_max_verify_attempts:
            otp_request.expires_at = now
            self.auth_otp_request_repo.update(otp_request)
            raise ValueError("invalid authentication")

        expected_hash = self._hash_otp_code(normalized_otp)
        if not hmac.compare_digest(expected_hash, otp_request.otp_hash):
            otp_request.attempt_count = current_attempt_count + 1
            if otp_request.attempt_count >= self.settings.auth_otp_max_verify_attempts:
                otp_request.expires_at = now
            self.auth_otp_request_repo.update(otp_request)
            raise ValueError("invalid authentication")

        otp_request.expires_at = now
        otp_request.attempt_count = 0
        self.auth_otp_request_repo.update(otp_request)

        user = self.user_repo.get_by_email(normalized_email)
        if not user:
            derived_name = normalized_email.split("@")[0] or normalized_email
            user = self.user_repo.create_user(email=normalized_email, full_name=derived_name)

        user = self.user_repo.update_last_login(user.id, now)
        session_token = self._build_session_token(user.id, user.email, now)

        return {
            "session_token": session_token,
            "user": {
                "id": int(user.id),
                "email": str(user.email),
            },
        }

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

    def _build_session_token(self, user_id: int, email: str, issued_at: datetime) -> str:
        expires_at = issued_at + timedelta(minutes=self.settings.auth_session_expiry_minutes)
        payload = {
            "user_id": user_id,
            "email": email,
            "issued_at": issued_at.isoformat(),
            "expiry": expires_at.isoformat(),
            "audience": self.settings.auth_session_audience,
        }
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload_bytes = payload_json.encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{payload_b64}.{signature_b64}"

    def get_authenticated_user(self, session_token: str | None) -> dict[str, int | str]:
        if not session_token:
            raise ValueError("invalid auth session")

        try:
            payload_segment, signature_segment = session_token.split(".", 1)
        except ValueError:
            raise ValueError("invalid auth session")

        expected_signature = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode("utf-8").rstrip("=")
        if not hmac.compare_digest(signature_segment, expected_signature_b64):
            raise ValueError("invalid auth session")

        payload = self._decode_session_payload(payload_segment)
        if payload.get("audience") != self.settings.auth_session_audience:
            raise ValueError("invalid auth session")

        expiry = payload.get("expiry")
        if not expiry:
            raise ValueError("invalid auth session")

        expires_at = datetime.fromisoformat(str(expiry))
        if datetime.now(timezone.utc) > self._to_utc(expires_at):
            raise ValueError("invalid auth session")

        email = payload.get("email")
        if not isinstance(email, str) or not email:
            raise ValueError("invalid auth session")

        user = self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("invalid auth session")

        return {
            "id": int(user.id),
            "email": str(user.email),
        }

    def _decode_session_payload(self, payload_segment: str) -> dict[str, object]:
        padded_segment = payload_segment + "=" * (-len(payload_segment) % 4)
        try:
            decoded_bytes = base64.urlsafe_b64decode(padded_segment.encode("utf-8"))
            return json.loads(decoded_bytes.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
            raise ValueError("invalid auth session")

    def _to_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


