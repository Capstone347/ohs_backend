from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.auth_service import AuthService


def make_settings() -> SimpleNamespace:
    return SimpleNamespace(
        secret_key="test-secret-key",
        auth_otp_ttl_minutes=10,
        auth_otp_resend_cooldown_seconds=60,
        auth_otp_email_rate_limit_count=5,
        auth_otp_ip_rate_limit_count=6,
        auth_otp_rate_limit_window_minutes=15,
        auth_otp_lockout_minutes=15,
    )


def make_service() -> tuple[AuthService, MagicMock, MagicMock, MagicMock, MagicMock, SimpleNamespace]:
    auth_otp_request_repo = MagicMock()
    user_repo = MagicMock()
    email_service = MagicMock()
    email_template_renderer = MagicMock()
    settings = make_settings()

    service = AuthService(
        auth_otp_request_repo=auth_otp_request_repo,
        user_repo=user_repo,
        email_service=email_service,
        email_template_renderer=email_template_renderer,
        settings=settings,
    )

    auth_otp_request_repo.count_recent_by_ip.return_value = 0

    return service, auth_otp_request_repo, user_repo, email_service, email_template_renderer, settings


def test_request_otp_persists_hashed_otp_for_unknown_user_without_sending_email():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    auth_repo.get_latest_by_email.return_value = None
    user_repo.get_by_email.return_value = None

    service.request_otp("USER@Example.com", "203.0.113.7")

    auth_repo.upsert_otp_request.assert_called_once()
    kwargs = auth_repo.upsert_otp_request.call_args.kwargs

    assert kwargs["email"] == "user@example.com"
    assert kwargs["otp_hash"]
    assert kwargs["otp_hash"] != "123456"
    assert len(kwargs["otp_hash"]) == 64
    assert kwargs["request_ip"] == "203.0.113.7"
    assert kwargs["attempt_count"] == 0
    assert kwargs["expires_at"] > kwargs["sent_at"]

    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()


def test_request_otp_returns_early_during_cooldown():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    now = datetime.now(timezone.utc)
    auth_repo.get_latest_by_email.return_value = SimpleNamespace(
        lockout_until=None,
        last_sent_at=now - timedelta(seconds=30),
        created_at=now - timedelta(seconds=30),
        attempt_count=0,
    )

    service.request_otp("test@example.com", "203.0.113.7")

    auth_repo.upsert_otp_request.assert_not_called()
    auth_repo.set_lockout.assert_not_called()
    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()
    user_repo.get_by_email.assert_not_called()


def test_request_otp_sets_lockout_when_ip_rate_limit_is_reached():
    service, auth_repo, user_repo, email_service, renderer, settings = make_service()

    auth_repo.get_latest_by_email.return_value = None
    auth_repo.count_recent_by_ip.return_value = settings.auth_otp_ip_rate_limit_count

    service.request_otp("test@example.com", "203.0.113.8")

    auth_repo.set_lockout.assert_called_once()
    auth_repo.upsert_otp_request.assert_not_called()
    user_repo.get_by_email.assert_not_called()
    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()


def test_request_otp_sets_lockout_when_email_limit_is_reached():
    service, auth_repo, user_repo, email_service, renderer, settings = make_service()

    now = datetime.now(timezone.utc)
    auth_repo.get_latest_by_email.return_value = SimpleNamespace(
        lockout_until=None,
        last_sent_at=now - timedelta(minutes=2),
        created_at=now - timedelta(minutes=1),
        attempt_count=settings.auth_otp_email_rate_limit_count - 1,
    )

    service.request_otp("test@example.com", "203.0.113.9")

    auth_repo.set_lockout.assert_called_once()
    auth_repo.upsert_otp_request.assert_not_called()
    user_repo.get_by_email.assert_not_called()
    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()


def test_request_otp_increments_attempt_count_within_window():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    now = datetime.now(timezone.utc)
    auth_repo.get_latest_by_email.return_value = SimpleNamespace(
        lockout_until=None,
        last_sent_at=now - timedelta(minutes=3),
        created_at=now - timedelta(minutes=2),
        attempt_count=1,
    )
    user_repo.get_by_email.return_value = None

    service.request_otp("test@example.com", None)

    auth_repo.upsert_otp_request.assert_called_once()
    kwargs = auth_repo.upsert_otp_request.call_args.kwargs
    assert kwargs["attempt_count"] == 2

    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()


def test_request_otp_sends_email_for_known_user():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    auth_repo.get_latest_by_email.return_value = None
    user_repo.get_by_email.return_value = SimpleNamespace(id=1, email="known@example.com")
    renderer.render_auth_otp.return_value = "<p>otp</p>"

    service.request_otp("known@example.com", "198.51.100.4")

    auth_repo.upsert_otp_request.assert_called_once()
    renderer.render_auth_otp.assert_called_once()
    email_service.send_transactional_email.assert_called_once()


def test_request_otp_swallows_email_sending_errors_to_keep_generic_flow():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    auth_repo.get_latest_by_email.return_value = None
    user_repo.get_by_email.return_value = SimpleNamespace(id=1, email="known@example.com")
    renderer.render_auth_otp.return_value = "<p>otp</p>"
    email_service.send_transactional_email.side_effect = RuntimeError("smtp down")

    service.request_otp("known@example.com", "198.51.100.5")

    auth_repo.upsert_otp_request.assert_called_once()
    email_service.send_transactional_email.assert_called_once()


def test_request_otp_returns_early_when_lockout_is_active():
    service, auth_repo, user_repo, email_service, renderer, _ = make_service()

    auth_repo.get_latest_by_email.return_value = SimpleNamespace(
        lockout_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        attempt_count=2,
    )

    service.request_otp("test@example.com", "198.51.100.10")

    auth_repo.count_recent_by_ip.assert_not_called()
    auth_repo.upsert_otp_request.assert_not_called()
    auth_repo.set_lockout.assert_not_called()
    user_repo.get_by_email.assert_not_called()
    renderer.render_auth_otp.assert_not_called()
    email_service.send_transactional_email.assert_not_called()


