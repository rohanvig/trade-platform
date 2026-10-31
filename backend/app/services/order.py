from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus, OrderType
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate


class OrderService:

    def __init__(self, db: Session):
        self.repository = OrderRepository(db)

    def create_order(
        self,
        user_id: int,
        order_data: OrderCreate,
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

        return self.repository.create(order)

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

    def get_user_orders(
        self,
        user_id: int,
    ) -> list[Order]:

        return self.repository.get_by_user(user_id)