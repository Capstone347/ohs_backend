from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserRole
from app.repositories.base_repository import BaseRepository, DuplicateRecordError


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        if not email:
            raise ValueError("email is required")
        
        return self.db.query(User).filter(User.email == email).first()

    def get_by_email_or_fail(self, email: str) -> User:
        user = self.get_by_email(email)
        if not user:
            from app.repositories.base_repository import RecordNotFoundError
            raise RecordNotFoundError(f"User with email {email} not found")
        return user

    def email_exists(self, email: str) -> bool:
        if not email:
            raise ValueError("email is required")
        
        return self.db.query(User).filter(User.email == email).first() is not None

    def create_user(self, email: str, full_name: str, role: UserRole = UserRole.CUSTOMER) -> User:
        if not email:
            raise ValueError("email is required")
        
        if not full_name:
            raise ValueError("full_name is required")
        
        if self.email_exists(email):
            raise DuplicateRecordError(f"User with email {email} already exists")
        
        user = User(
            email=email,
            full_name=full_name,
            role=role.value,
            created_at=datetime.now(timezone.utc)
        )
        return self.create(user)

    def get_by_id_with_company(self, user_id: int) -> User | None:
        if not user_id:
            raise ValueError("user_id is required")
        
        return (
            self.db.query(User)
            .options(joinedload(User.company))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_id_with_orders(self, user_id: int) -> User | None:
        if not user_id:
            raise ValueError("user_id is required")
        
        return (
            self.db.query(User)
            .options(joinedload(User.orders))
            .filter(User.id == user_id)
            .first()
        )

    def get_users_by_role(self, role: UserRole) -> list[User]:
        if not role:
            raise ValueError("role is required")
        
        return self.db.query(User).filter(User.role == role).all()

    def get_users_by_company_id(self, company_id: int) -> list[User]:
        if not company_id:
            raise ValueError("company_id is required")
        
        return (
            self.db.query(User)
            .filter(User.company_id == company_id)
            .order_by(User.created_at.desc())
            .all()
        )

    def update_last_login(self, user_id: int, login_time: datetime) -> User:
        if not user_id:
            raise ValueError("user_id is required")
        
        if not login_time:
            raise ValueError("login_time is required")
        
        user = self.get_by_id_or_fail(user_id)
        user.last_login = login_time
        return self.update(user)

    def set_otp_token(self, user_id: int, otp_token: str, otp_expires: datetime) -> User:
        if not user_id:
            raise ValueError("user_id is required")
        
        if not otp_token:
            raise ValueError("otp_token is required")
        
        if not otp_expires:
            raise ValueError("otp_expires is required")
        
        user = self.get_by_id_or_fail(user_id)
        user.otp_token = otp_token
        user.otp_expires = otp_expires
        return self.update(user)

    def clear_otp_token(self, user_id: int) -> User:
        if not user_id:
            raise ValueError("user_id is required")
        
        user = self.get_by_id_or_fail(user_id)
        user.otp_token = None
        user.otp_expires = None
        return self.update(user)

    def verify_otp(self, email: str, otp_token: str) -> User | None:
        if not email:
            raise ValueError("email is required")
        
        if not otp_token:
            raise ValueError("otp_token is required")
        
        user = self.get_by_email(email)
        
        if not user:
            return None
        
        if not user.otp_token or not user.otp_expires:
            return None
        
        if user.otp_token != otp_token:
            return None
        
        if datetime.now(timezone.utc) > user.otp_expires:
            return None
        
        return user

    def update_password_hash(self, user_id: int, password_hash: str) -> User:
        if not user_id:
            raise ValueError("user_id is required")
        
        if not password_hash:
            raise ValueError("password_hash is required")
        
        user = self.get_by_id_or_fail(user_id)
        user.password_hash = password_hash
        return self.update(user)

    def assign_to_company(self, user_id: int, company_id: int) -> User:
        if not user_id:
            raise ValueError("user_id is required")
        
        if not company_id:
            raise ValueError("company_id is required")
        
        user = self.get_by_id_or_fail(user_id)
        user.company_id = company_id
        return self.update(user)

    def get_admin_users(self) -> list[User]:
        return self.get_users_by_role(UserRole.ADMIN)

    def get_customer_users(self) -> list[User]:
        return self.get_users_by_role(UserRole.CUSTOMER)
