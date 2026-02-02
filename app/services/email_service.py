from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional
import logging

import re

from app.config import settings
from app.repositories.email_log_repository import EmailLogRepository
from app.models.email_log import EmailStatus


class EmailService:
    def __init__(self, email_log_repo: EmailLogRepository, smtp_settings: object = settings):
        self.email_log_repo = email_log_repo
        self.smtp_host = smtp_settings.smtp_host
        self.smtp_port = smtp_settings.smtp_port
        self.smtp_user = smtp_settings.smtp_user
        self.smtp_password = smtp_settings.smtp_password
        self.from_email = smtp_settings.smtp_from_email
        self.from_name = smtp_settings.smtp_from_name
        self.smtp_use_ssl = getattr(smtp_settings, "smtp_use_ssl", False)
        self.smtp_use_starttls = getattr(smtp_settings, "smtp_use_starttls", True)
        self.logger = logging.getLogger(__name__)

    def _build_message(self, recipient: str, subject: str, html_body: str, attachment_path: Optional[Path] = None) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        if attachment_path:
            if not Path(attachment_path).exists():
                raise FileNotFoundError(f"Attachment not found: {attachment_path}")

            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document")
                part.add_header("Content-Disposition", "attachment", filename=Path(attachment_path).name)
                msg.attach(part)

        return msg

    def send_email(self, order_id: int, recipient_email: str, subject: str, html_body: str, attachment_path: Optional[Path] = None) -> None:
        email_log = self.email_log_repo.create_email_log(order_id, recipient_email, subject)

        already_failed = False

        try:
            if not re.match(r"[^@]+@[^@]+\.[^@]+$", recipient_email):
                try:
                    self.email_log_repo.mark_as_failed(email_log.id, "invalid recipient email")
                    already_failed = True
                except Exception:
                    pass
                raise ValueError("invalid recipient email")

            msg = self._build_message(recipient_email, subject, html_body, attachment_path)

            if self.smtp_use_ssl:
                smtp_class = smtplib.SMTP_SSL
            else:
                smtp_class = smtplib.SMTP

            with smtp_class(self.smtp_host, self.smtp_port, timeout=10) as server:
                if not self.smtp_use_ssl and self.smtp_use_starttls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            self.email_log_repo.mark_as_delivered(email_log.id)

        except Exception as exc:
            try:
                if not already_failed:
                    self.email_log_repo.mark_as_failed(email_log.id, str(exc))
            except Exception:
                pass
            self.logger.error("email send failed", exc_info=True, extra={"order_id": order_id, "recipient": recipient_email})
            raise
