from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class Candle(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    model_config = ConfigDict(from_attributes=True)


class QuoteResponse(BaseModel):
    symbol: str
    price: Decimal
    currency: str = "USD"
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    volume: int | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoricalDataResponse(BaseModel):
    symbol: str
    timeframe: str
    count: int
    candles: list[Candle]

    model_config = ConfigDict(from_attributes=True)


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    quote_type: str | None = None
