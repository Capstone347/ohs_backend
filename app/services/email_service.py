from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import logging
import re

from app.config import Settings
from app.repositories.email_log_repository import EmailLogRepository

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
SMTP_TIMEOUT_SECONDS = 30


class EmailService:
    def __init__(self, email_log_repo: EmailLogRepository, smtp_settings: Settings):
        self.email_log_repo = email_log_repo
        self.smtp_host = smtp_settings.smtp_host
        self.smtp_port = smtp_settings.smtp_port
        self.smtp_user = smtp_settings.smtp_user
        self.smtp_password = smtp_settings.smtp_password
        self.from_email = smtp_settings.smtp_from_email
        self.from_name = smtp_settings.smtp_from_name
        # Accept smtp settings objects that may omit optional flags (tests use SimpleNamespace)
        self.smtp_use_ssl = getattr(smtp_settings, "smtp_use_ssl", False)
        self.smtp_use_starttls = getattr(smtp_settings, "smtp_use_starttls", True)
        self.logger = logging.getLogger(__name__)

    def send_email(
        self,
        order_id: int,
        recipient_email: str,
        subject: str,
        html_body: str,
        attachment_path: Path | None = None
    ) -> None:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not recipient_email:
            raise ValueError("recipient_email is required")
        
        if not subject:
            raise ValueError("subject is required")
        
        if not html_body:
            raise ValueError("html_body is required")
        
        if not self._is_valid_email(recipient_email):
            raise ValueError(f"invalid email format: {recipient_email}")
        
        if attachment_path and not attachment_path.exists():
            raise FileNotFoundError(f"attachment not found: {attachment_path}")
        
        email_log = self.email_log_repo.create_email_log(order_id, recipient_email, subject)
        
        try:
            self._send_smtp_message(recipient_email, subject, html_body, attachment_path)
            self.email_log_repo.mark_as_delivered(email_log.id)
            
        except Exception as exc:
            self.email_log_repo.mark_as_failed(email_log.id, str(exc))
            self.logger.error(
                "email send failed",
                exc_info=True,
                extra={"order_id": order_id, "recipient": recipient_email}
            )
            raise

    def send_transactional_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
    ) -> None:
        if not recipient_email:
            raise ValueError("recipient_email is required")

        if not subject:
            raise ValueError("subject is required")

        if not html_body:
            raise ValueError("html_body is required")

        if not self._is_valid_email(recipient_email):
            raise ValueError(f"invalid email format: {recipient_email}")

        self._send_smtp_message(recipient_email, subject, html_body, None)

    def _is_valid_email(self, email: str) -> bool:
        return bool(re.match(EMAIL_REGEX, email))

    def _send_smtp_message(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        attachment_path: Path | None
    ) -> None:
        msg = self._build_message(recipient, subject, html_body, attachment_path)
        
        smtp_class = smtplib.SMTP_SSL if self.smtp_use_ssl else smtplib.SMTP
        
        with smtp_class(self.smtp_host, self.smtp_port, timeout=SMTP_TIMEOUT_SECONDS) as server:
            if not self.smtp_use_ssl and self.smtp_use_starttls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

    def _build_message(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        attachment_path: Path | None
    ) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        if attachment_path:
            self._attach_document(msg, attachment_path)

        return msg

    def _attach_document(self, msg: MIMEMultipart, attachment_path: Path) -> None:
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(
                f.read(),
                _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            part.add_header("Content-Disposition", "attachment", filename=attachment_path.name)
            msg.attach(part)
