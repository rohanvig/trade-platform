from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

class UserService:

    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create_user(self, data: UserCreate) -> User:

        existing_user = self.repository.get_by_email(data.email)

        if existing_user:
            raise ValueError("Email already registered")

        existing_username = self.repository.get_by_username(
            data.username
        )

        if existing_username:
            raise ValueError("Username already registered")

        user = User(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
        )

        return self.repository.create(user)

    def login(self, email: str, password: str) -> str:
        user = self.repository.get_by_email(email)

        if not user:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("User account is inactive")

        return create_access_token(user.id) 