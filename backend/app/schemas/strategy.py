from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.strategies.base import SignalType


class SignalResponse(BaseModel):
    timestamp: datetime
    symbol: str
    signal: SignalType
    price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = ""
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class StrategyMetadata(BaseModel):
    name: str
    description: str
    default_params: dict

    model_config = ConfigDict(from_attributes=True)


class StrategyRunRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, examples=["AAPL"])
    strategy_name: str = Field(examples=["SMA_CROSSOVER"])
    params: dict = Field(default_factory=dict)
    timeframe: str = Field(default="1d", examples=["1d"])
    period_range: str = Field(default="1y", examples=["1y"])


class StrategyRunResponse(BaseModel):
    symbol: str
    strategy_name: str
    total_signals: int
    buy_signals: int
    sell_signals: int
    latest_signal: SignalResponse | None = None
    signals: list[SignalResponse]

    model_config = ConfigDict(from_attributes=True)
