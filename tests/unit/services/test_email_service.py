import smtplib
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.email_service import EmailService
from app.repositories.email_log_repository import EmailLogRepository


class DummySMTP:

    def __init__(self, *args, **kwargs):
        self.started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started = True

    def login(self, user, password):
        return True

    def send_message(self, msg):
        return True


def make_smtp_settings():
    return SimpleNamespace(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_from_email="noreply@example.com",
        smtp_from_name="OHS Remote",
    )


def test_send_email_with_attachment_success(monkeypatch, tmp_path):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    mock_repo = MagicMock(spec=EmailLogRepository)
    mock_repo.create_email_log.return_value = SimpleNamespace(id=1)

    service = EmailService(mock_repo, smtp_settings=make_smtp_settings())

    attachment = tmp_path / "doc.docx"
    attachment.write_bytes(b"dummy docx content")

    service.send_email(order_id=10, recipient_email="test@example.com", subject="Test", html_body="<p>hi</p>", attachment_path=attachment)

    mock_repo.create_email_log.assert_called_once_with(10, "test@example.com", "Test")
    mock_repo.mark_as_delivered.assert_called_once_with(1)


def test_send_email_without_attachment_success(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    mock_repo = MagicMock(spec=EmailLogRepository)
    mock_repo.create_email_log.return_value = SimpleNamespace(id=2)

    service = EmailService(mock_repo, smtp_settings=make_smtp_settings())

    service.send_email(order_id=20, recipient_email="noattach@example.com", subject="NoAttach", html_body="<p>ok</p>")

    mock_repo.create_email_log.assert_called_once_with(20, "noattach@example.com", "NoAttach")
    mock_repo.mark_as_delivered.assert_called_once_with(2)


def test_send_email_missing_attachment_marks_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    mock_repo = MagicMock(spec=EmailLogRepository)
    mock_repo.create_email_log.return_value = SimpleNamespace(id=3)

    service = EmailService(mock_repo, smtp_settings=make_smtp_settings())

    missing = tmp_path / "does_not_exist.docx"

    with pytest.raises(FileNotFoundError):
        service.send_email(order_id=30, recipient_email="missing@example.com", subject="Missing", html_body="<p>hi</p>", attachment_path=missing)

    mock_repo.create_email_log.assert_called_once_with(30, "missing@example.com", "Missing")
    mock_repo.mark_as_failed.assert_called_once()


def test_send_email_smtp_recipient_refused(monkeypatch):

    class RecipientRefusingSMTP(DummySMTP):
        def send_message(self, msg):
            raise smtplib.SMTPRecipientsRefused({'to': (550, b'refused')})

    monkeypatch.setattr(smtplib, "SMTP", RecipientRefusingSMTP)

    mock_repo = MagicMock(spec=EmailLogRepository)
    mock_repo.create_email_log.return_value = SimpleNamespace(id=4)

    service = EmailService(mock_repo, smtp_settings=make_smtp_settings())

    with pytest.raises(smtplib.SMTPRecipientsRefused):
        service.send_email(order_id=40, recipient_email="badaddr@example.com", subject="BadAddr", html_body="<p>hi</p>")

    mock_repo.create_email_log.assert_called_once_with(40, "badaddr@example.com", "BadAddr")
    mock_repo.mark_as_failed.assert_called_once()


def test_create_email_log_raises_propagates(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    mock_repo = MagicMock(spec=EmailLogRepository)
    mock_repo.create_email_log.side_effect = ValueError("order_id required")

    service = EmailService(mock_repo, smtp_settings=make_smtp_settings())

    with pytest.raises(ValueError):
        service.send_email(order_id=None, recipient_email="x@example.com", subject="X", html_body="<p>x</p>")

    mock_repo.create_email_log.assert_called_once()
    mock_repo.mark_as_failed.assert_not_called()
