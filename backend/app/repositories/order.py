from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order


class OrderRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return order

    def get_by_id(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)

        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user(
        self,
        user_id: int,
    ) -> list[Order]:

        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )

        return list(self.db.execute(stmt).scalars().all())