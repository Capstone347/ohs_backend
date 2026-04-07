from datetime import datetime

from sqlalchemy.orm import Session

from app.models.admin_user import AdminRole, AdminUser
from app.repositories.base_repository import BaseRepository, RecordNotFoundError


class AdminUserRepository(BaseRepository[AdminUser]):
    def __init__(self, db: Session):
        super().__init__(AdminUser, db)

    def get_by_email(self, email: str) -> AdminUser | None:
        if not email:
            raise ValueError("email is required")

        return self.db.query(AdminUser).filter(AdminUser.email == email.strip().lower()).first()

    def get_by_email_or_fail(self, email: str) -> AdminUser:
        admin = self.get_by_email(email)
        if not admin:
            raise RecordNotFoundError(f"AdminUser with email {email} not found")
        return admin

    def get_all_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AdminUser], int]:
        query = self.db.query(AdminUser)
        total = query.count()
        items = query.order_by(AdminUser.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def create_admin(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        role: AdminRole = AdminRole.MANAGER,
    ) -> AdminUser:
        admin = AdminUser(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            password_hash=password_hash,
            role=role.value,
        )
        return self.create(admin)

    def update_last_login(self, admin_id: int, login_time: datetime) -> AdminUser:
        admin = self.get_by_id_or_fail(admin_id)
        admin.last_login = login_time
        return self.update(admin)

    def update_password_hash(self, admin_id: int, password_hash: str) -> AdminUser:
        admin = self.get_by_id_or_fail(admin_id)
        admin.password_hash = password_hash
        return self.update(admin)

    def deactivate(self, admin_id: int) -> AdminUser:
        admin = self.get_by_id_or_fail(admin_id)
        admin.is_active = False
        return self.update(admin)
