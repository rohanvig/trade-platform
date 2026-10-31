from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PositionResponse(BaseModel):
    symbol: str
    quantity: int
    average_buy_price: Decimal
    current_price: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal

    model_config = ConfigDict(from_attributes=True)


class PortfolioResponse(BaseModel):
    user_id: int
    cash_balance: Decimal
    total_invested: Decimal
    total_holdings_value: Decimal
    total_portfolio_value: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: Decimal
    positions: list[PositionResponse]

    model_config = ConfigDict(from_attributes=True)
