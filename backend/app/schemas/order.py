from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderSide, OrderStatus, OrderType


class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    side: OrderSide
    quantity: int = Field(gt=0)
    order_type: OrderType
    price: Decimal | None = Field(default=None, gt=0)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Decimal | None
    status: OrderStatus
    broker_order_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)