from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio, Position


class PortfolioRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_portfolio_by_user(self, user_id: int) -> Portfolio | None:
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create_portfolio(
        self,
        user_id: int,
        initial_cash: Decimal = Decimal("100000.00"),
    ) -> Portfolio:
        portfolio = self.get_portfolio_by_user(user_id)
        if portfolio is None:
            portfolio = Portfolio(
                user_id=user_id,
                cash_balance=initial_cash,
            )
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
        return portfolio

    def update_portfolio(self, portfolio: Portfolio) -> Portfolio:
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def get_positions(self, user_id: int) -> list[Position]:
        stmt = select(Position).where(
            Position.user_id == user_id,
            Position.quantity > 0,
        ).order_by(Position.symbol.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_position_by_symbol(self, user_id: int, symbol: str) -> Position | None:
        stmt = select(Position).where(
            Position.user_id == user_id,
            Position.symbol == symbol.upper(),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def save_position(self, position: Position) -> Position:
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def delete_position(self, position: Position) -> None:
        self.db.delete(position)
        self.db.commit()
