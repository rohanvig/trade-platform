from datetime import datetime
from pydantic import BaseModel, ConfigDict


class IndicatorValuePoint(BaseModel):
    timestamp: datetime
    value: float | None

    model_config = ConfigDict(from_attributes=True)


class MACDValuePoint(BaseModel):
    timestamp: datetime
    macd: float | None
    signal: float | None
    histogram: float | None

    model_config = ConfigDict(from_attributes=True)


class BollingerBandsValuePoint(BaseModel):
    timestamp: datetime
    upper: float | None
    middle: float | None
    lower: float | None

    model_config = ConfigDict(from_attributes=True)


class SingleIndicatorResponse(BaseModel):
    symbol: str
    indicator: str
    params: dict
    points: list[IndicatorValuePoint]

    model_config = ConfigDict(from_attributes=True)


class MACDResponse(BaseModel):
    symbol: str
    indicator: str = "MACD"
    fast_period: int
    slow_period: int
    signal_period: int
    points: list[MACDValuePoint]

    model_config = ConfigDict(from_attributes=True)


class BollingerBandsResponse(BaseModel):
    symbol: str
    indicator: str = "BOLLINGER_BANDS"
    period: int
    std_multiplier: float
    points: list[BollingerBandsValuePoint]

    model_config = ConfigDict(from_attributes=True)
