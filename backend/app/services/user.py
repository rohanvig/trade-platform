from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


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
            password_hash=data.password,  # TEMPORARY
        )

        return self.repository.create(user)