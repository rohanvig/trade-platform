from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


class CryptoQuote(BaseModel):
    """Reference spot index observation (NOT a tradable candle)."""

    underlying: str  # "BTC" or "ETH"
    index_name: str  # "btc_usd" or "eth_usd"
    index_price: Decimal  # Reference price in USD
    estimated_delivery_price: Decimal | None = None
    is_index: bool = True
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("index_price", "estimated_delivery_price", mode="before")
    @classmethod
    def _validate_decimals(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)


class CryptoCandle(BaseModel):
    """Traded instrument OHLCV bar (e.g. BTC-PERPETUAL)."""

    instrument_name: str  # "BTC-PERPETUAL" or "ETH-PERPETUAL"
    timeframe: str  # "1d", "4h", "1h"
    timestamp: datetime  # UTC bucket start timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal  # Base asset traded volume
    is_closed: bool = True  # False if bucket is still actively forming

    model_config = ConfigDict(from_attributes=True)

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def _validate_decimals(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)


class OptionContractSummary(BaseModel):
    """Joined active option contract with market depth metrics."""

    instrument_name: str  # e.g. "BTC-27DEC26-100000-C"
    underlying: str  # "BTC" or "ETH"
    strike: Decimal  # Option strike in USD
    option_type: str  # "CALL" or "PUT"
    expiry_date: date  # Expiration date
    expiration_timestamp: int  # Milliseconds UTC
    contract_size: Decimal = Decimal("1.0")
    settlement_currency: str  # "BTC", "ETH", or "USDC"
    quote_currency: str = "USD"  # "USD", "USDC", "BTC", "ETH"

    # Pricing metrics (Nullable for illiquid / deep OTM strikes)
    mark_price_raw: Decimal | None = None  # Quoted in exchange denomination
    mark_price_usd: Decimal | None = None  # Converted to USD
    mark_iv: Decimal | None = None  # Annualized Implied Volatility %
    bid_price_raw: Decimal | None = None
    ask_price_raw: Decimal | None = None
    bid_price_usd: Decimal | None = None
    ask_price_usd: Decimal | None = None

    # Liquidity & Freshness
    open_interest: Decimal = Decimal("0")
    is_oi_delayed: bool = True  # Deribit 8-hour refresh indicator
    volume_usd: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "strike",
        "contract_size",
        "mark_price_raw",
        "mark_price_usd",
        "mark_iv",
        "bid_price_raw",
        "ask_price_raw",
        "bid_price_usd",
        "ask_price_usd",
        "open_interest",
        "volume_usd",
        mode="before",
    )
    @classmethod
    def _validate_decimals(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)

    @field_validator("option_type", mode="before")
    @classmethod
    def _standardize_option_type(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in ("C", "CALL"):
                return "CALL"
            if v_upper in ("P", "PUT"):
                return "PUT"
            return v_upper
        return str(v)


class OptionChainResponse(BaseModel):
    """Complete strike ladder response partitioned by contract type."""

    underlying: str
    expiry_date: date
    underlying_index_price: Decimal
    calls: list[OptionContractSummary] = Field(default_factory=list)
    puts: list[OptionContractSummary] = Field(default_factory=list)
    total_contracts: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("underlying_index_price", mode="before")
    @classmethod
    def _validate_decimals(cls, v: Any) -> Decimal | None:
        return _to_decimal(v)


class CryptoErrorResponse(BaseModel):
    """Uniform error response schema."""

    error_code: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
