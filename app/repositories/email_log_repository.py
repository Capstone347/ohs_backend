from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.email_log import EmailLog, EmailStatus
from app.repositories.base_repository import BaseRepository


class EmailLogRepository(BaseRepository[EmailLog]):
    def __init__(self, db: Session):
        super().__init__(EmailLog, db)

    def get_by_order_id(self, order_id: int) -> list[EmailLog]:
        if not order_id:
            raise ValueError("order_id is required")
        
        return (
            self.db.query(EmailLog)
            .filter(EmailLog.order_id == order_id)
            .order_by(EmailLog.sent_at.desc())
            .all()
        )

    def get_by_recipient_email(self, recipient_email: str) -> list[EmailLog]:
        if not recipient_email:
            raise ValueError("recipient_email is required")
        
        return (
            self.db.query(EmailLog)
            .filter(EmailLog.recipient_email == recipient_email)
            .order_by(EmailLog.sent_at.desc())
            .all()
        )

    def get_by_status(self, status: EmailStatus) -> list[EmailLog]:
        if not status:
            raise ValueError("status is required")
        
        return (
            self.db.query(EmailLog)
            .filter(EmailLog.status == status)
            .order_by(EmailLog.sent_at.desc())
            .all()
        )

    def create_email_log(
        self,
        order_id: int,
        recipient_email: str,
        subject: str,
        status: EmailStatus = EmailStatus.PENDING,
        failure_reason: str | None = None
    ) -> EmailLog:
        if not order_id:
            raise ValueError("order_id is required")
        
        if not recipient_email:
            raise ValueError("recipient_email is required")
        
        if not subject:
            raise ValueError("subject is required")
        
        email_log = EmailLog(
            order_id=order_id,
            recipient_email=recipient_email,
            subject=subject,
            status=status,
            sent_at=datetime.utcnow(),
            failure_reason=failure_reason
        )
        return self.create(email_log)

    def update_status(
        self,
        email_log_id: int,
        status: EmailStatus,
        failure_reason: str | None = None
    ) -> EmailLog:
        if not email_log_id:
            raise ValueError("email_log_id is required")
        
        if not status:
            raise ValueError("status is required")
        
        email_log = self.get_by_id_or_fail(email_log_id)
        email_log.status = status
        if failure_reason:
            email_log.failure_reason = failure_reason
        return self.update(email_log)

    def mark_as_delivered(self, email_log_id: int) -> EmailLog:
        if not email_log_id:
            raise ValueError("email_log_id is required")
        
        return self.update_status(email_log_id, EmailStatus.DELIVERED)

    def mark_as_failed(self, email_log_id: int, failure_reason: str) -> EmailLog:
        if not email_log_id:
            raise ValueError("email_log_id is required")
        
        if not failure_reason:
            raise ValueError("failure_reason is required")
        
        return self.update_status(email_log_id, EmailStatus.FAILED, failure_reason)

    def get_failed_emails(self) -> list[EmailLog]:
        return self.get_by_status(EmailStatus.FAILED)

    def get_sent_emails(self) -> list[EmailLog]:
        return self.get_by_status(EmailStatus.SENT)

    def get_delivered_emails(self) -> list[EmailLog]:
        return self.get_by_status(EmailStatus.DELIVERED)

    def get_emails_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[EmailLog]:
        if not start_date:
            raise ValueError("start_date is required")
        
        if not end_date:
            raise ValueError("end_date is required")
        
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        
        return (
            self.db.query(EmailLog)
            .filter(
                EmailLog.sent_at >= start_date,
                EmailLog.sent_at <= end_date
            )
            .order_by(EmailLog.sent_at.desc())
            .all()
        )

    def get_recent_emails(self, limit: int = 50) -> list[EmailLog]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return (
            self.db.query(EmailLog)
            .options(joinedload(EmailLog.order))
            .order_by(EmailLog.sent_at.desc())
            .limit(limit)
            .all()
        )

    def count_emails_for_order(self, order_id: int) -> int:
        if not order_id:
            raise ValueError("order_id is required")
        
        return self.db.query(EmailLog).filter(EmailLog.order_id == order_id).count()

    def count_emails_for_recipient(self, recipient_email: str) -> int:
        if not recipient_email:
            raise ValueError("recipient_email is required")
        
        return self.db.query(EmailLog).filter(EmailLog.recipient_email == recipient_email).count()

    def get_failed_emails_for_retry(self, limit: int = 100) -> list[EmailLog]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        
        return (
            self.db.query(EmailLog)
            .options(joinedload(EmailLog.order))
            .filter(EmailLog.status == EmailStatus.FAILED)
            .order_by(EmailLog.sent_at.asc())
            .limit(limit)
            .all()
        )
