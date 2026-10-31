from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus, OrderType
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate


class OrderService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = OrderRepository(db)

    def create_order(
        self,
        user_id: int,
        order_data: OrderCreate,
        execute_immediately: bool = False,
    ) -> Order:

        # LIMIT orders require a price
        if (
            order_data.order_type == OrderType.LIMIT
            and order_data.price is None
        ):
            raise ValueError(
                "Price is required for LIMIT orders"
            )

        # MARKET orders don't need a limit price
        if (
            order_data.order_type == OrderType.MARKET
            and order_data.price is not None
        ):
            raise ValueError(
                "Price should not be provided for MARKET orders"
            )

        order = Order(
            user_id=user_id,
            symbol=order_data.symbol.upper(),
            side=order_data.side,
            quantity=order_data.quantity,
            order_type=order_data.order_type,
            price=order_data.price,
            status=OrderStatus.PENDING,
        )

        order = self.repository.create(order)

        if execute_immediately:
            from app.services.portfolio import PortfolioService
            portfolio_service = PortfolioService(self.db)
            return portfolio_service.execute_paper_order(order)

        return order

    def execute_order(
        self,
        order_id: int,
        user_id: int,
    ) -> Order:
        order = self.repository.get_by_id(order_id)

        if order is None or order.user_id != user_id:
            raise KeyError("Order not found")

        if order.status not in (OrderStatus.PENDING, OrderStatus.OPEN):
            raise ValueError(
                f"Cannot execute order with status '{order.status.value}'"
            )

        from app.services.portfolio import PortfolioService
        portfolio_service = PortfolioService(self.db)
        return portfolio_service.execute_paper_order(order)

    def get_order(
        self,
        order_id: int,
        user_id: int,
    ) -> Order | None:

        order = self.repository.get_by_id(order_id)

        if order is None:
            return None

        # Users can only access their own orders
        if order.user_id != user_id:
            return None

        return order

    def cancel_order(
        self,
        order_id: int,
        user_id: int,
    ) -> Order:
        order = self.repository.get_by_id(order_id)

        if order is None or order.user_id != user_id:
            raise KeyError("Order not found")

        if order.status not in (OrderStatus.PENDING, OrderStatus.OPEN):
            raise ValueError(
                f"Cannot cancel order with status '{order.status.value}'"
            )

        order.status = OrderStatus.CANCELLED
        return self.repository.update(order)

    def get_user_orders(
        self,
        user_id: int,
        status: OrderStatus | None = None,
        symbol: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:

        return self.repository.get_by_user(
            user_id=user_id,
            status=status,
            symbol=symbol,
            limit=limit,
            offset=offset,
        )