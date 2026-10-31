from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TradeSchema(BaseModel):
    id: int
    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    exit_reason: str
    commission: float

    model_config = ConfigDict(from_attributes=True)


class EquityPointSchema(BaseModel):
    timestamp: datetime
    equity: float
    cash: float
    holdings_value: float
    drawdown_pct: float

    model_config = ConfigDict(from_attributes=True)


class BacktestMetricsSchema(BaseModel):
    initial_capital: float
    final_equity: float
    net_profit: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_trade_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float

    model_config = ConfigDict(from_attributes=True)


class BacktestRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, examples=["AAPL"])
    strategy_name: str = Field(examples=["SMA_CROSSOVER"])
    params: dict = Field(default_factory=dict)
    initial_capital: float = Field(default=10000.0, gt=0)
    commission_pct: float = Field(default=0.1, ge=0)
    slippage_pct: float = Field(default=0.05, ge=0)
    timeframe: str = Field(default="1d", examples=["1d"])
    period_range: str = Field(default="1y", examples=["1y"])


class BacktestResponse(BaseModel):
    symbol: str
    strategy_name: str
    parameters: dict
    metrics: BacktestMetricsSchema
    equity_curve: list[EquityPointSchema]
    trades: list[TradeSchema]

    model_config = ConfigDict(from_attributes=True)
