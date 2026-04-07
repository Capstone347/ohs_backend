import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt

from app.config import Settings
from app.repositories.admin_user_repository import AdminUserRepository

ADMIN_SESSION_AUDIENCE = "ohs-admin-auth"
ADMIN_SESSION_EXPIRY_MINUTES = 480


class AdminAuthService:
    def __init__(
        self,
        admin_user_repo: AdminUserRepository,
        settings: Settings,
    ):
        self.admin_user_repo = admin_user_repo
        self.settings = settings

    def login(self, email: str, password: str) -> dict[str, str | dict[str, int | str]]:
        if not email or not password:
            raise ValueError("email and password are required")

        normalized_email = email.strip().lower()
        admin = self.admin_user_repo.get_by_email(normalized_email)
        if not admin:
            raise ValueError("invalid credentials")

        if not admin.is_active:
            raise ValueError("account is deactivated")

        if not _bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
            raise ValueError("invalid credentials")

        now = datetime.now(UTC)
        self.admin_user_repo.update_last_login(admin.id, now)

        session_token = self._build_session_token(admin.id, admin.email, admin.role, now)

        return {
            "session_token": session_token,
            "admin": {
                "id": int(admin.id),
                "email": str(admin.email),
                "full_name": str(admin.full_name),
                "role": str(admin.role),
            },
        }

    def get_authenticated_admin(self, session_token: str | None) -> dict[str, int | str]:
        if not session_token:
            raise ValueError("invalid admin session")

        try:
            payload_segment, signature_segment = session_token.split(".", 1)
        except ValueError:
            raise ValueError("invalid admin session") from None

        expected_signature = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(signature_segment, expected_signature_b64):
            raise ValueError("invalid admin session")

        payload = self._decode_payload(payload_segment)

        if payload.get("audience") != ADMIN_SESSION_AUDIENCE:
            raise ValueError("invalid admin session")

        expiry = payload.get("expiry")
        if not expiry:
            raise ValueError("invalid admin session")

        expires_at = datetime.fromisoformat(str(expiry))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires_at:
            raise ValueError("invalid admin session")

        admin_email = payload.get("email")
        if not isinstance(admin_email, str) or not admin_email:
            raise ValueError("invalid admin session")

        admin = self.admin_user_repo.get_by_email(admin_email)
        if not admin:
            raise ValueError("invalid admin session")

        if not admin.is_active:
            raise ValueError("invalid admin session")

        return {
            "id": int(admin.id),
            "email": str(admin.email),
            "full_name": str(admin.full_name),
            "role": str(admin.role),
        }

    def change_password(
        self,
        admin_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        if not current_password or not new_password:
            raise ValueError("current_password and new_password are required")

        if len(new_password) < 8:
            raise ValueError("new_password must be at least 8 characters")

        admin = self.admin_user_repo.get_by_id_or_fail(admin_id)

        if not _bcrypt.checkpw(current_password.encode(), admin.password_hash.encode()):
            raise ValueError("current password is incorrect")

        new_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt()).decode()
        self.admin_user_repo.update_password_hash(admin_id, new_hash)

    def create_admin_user(
        self,
        email: str,
        full_name: str,
        password: str,
        role: str,
    ) -> dict[str, int | str]:
        if not email or not full_name or not password:
            raise ValueError("email, full_name, and password are required")

        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")

        from app.models.admin_user import AdminRole

        try:
            admin_role = AdminRole(role)
        except ValueError:
            raise ValueError(f"invalid role: {role}") from None

        existing = self.admin_user_repo.get_by_email(email.strip().lower())
        if existing:
            raise ValueError("an admin with this email already exists")

        password_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
        admin = self.admin_user_repo.create_admin(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=admin_role,
        )

        return {
            "id": int(admin.id),
            "email": str(admin.email),
            "full_name": str(admin.full_name),
            "role": str(admin.role),
        }

    def _build_session_token(
        self,
        admin_id: int,
        email: str,
        role: str,
        issued_at: datetime,
    ) -> str:
        expires_at = issued_at + timedelta(minutes=ADMIN_SESSION_EXPIRY_MINUTES)
        payload = {
            "admin_id": admin_id,
            "email": email,
            "role": role,
            "issued_at": issued_at.isoformat(),
            "expiry": expires_at.isoformat(),
            "audience": ADMIN_SESSION_AUDIENCE,
        }
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{payload_b64}.{signature_b64}"

    def _decode_payload(self, payload_segment: str) -> dict[str, object]:
        padded = payload_segment + "=" * (-len(payload_segment) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
            return json.loads(decoded.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("invalid admin session") from None
