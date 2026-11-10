from datetime import date
from typing import Any, Protocol, runtime_checkable

from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoQuote,
    OptionContractSummary,
)


@runtime_checkable
class MarketDataAdapter(Protocol):
    """Abstract asynchronous protocol for crypto market data ingestion."""

    async def get_index_price(self, underlying: str) -> CryptoQuote:
        """
        Fetch current reference spot index price for the given asset (e.g. BTC, ETH).
        Explicitly tagged as is_index=True (NOT a tradable candle).
        """
        ...

    async def get_instrument_candles(
        self,
        instrument_name: str,
        resolution: str,
        start_ts: int,
        end_ts: int,
    ) -> list[CryptoCandle]:
        """
        Fetch historical traded instrument OHLCV candles (e.g. BTC-PERPETUAL).
        """
        ...

    async def get_active_instruments(self, currency: str) -> list[dict[str, Any]]:
        """
        Fetch active instrument definitions for a currency (BTC, ETH),
        filtering strictly for state="open" and is_active=True.
        """
        ...

    async def get_book_summary(self, currency: str) -> list[dict[str, Any]]:
        """
        Fetch current book summary and ticker metrics across all active option contracts.
        """
        ...

    async def get_options_chain(
        self,
        underlying: str,
        expiry_date: date | None = None,
    ) -> list[OptionContractSummary]:
        """
        Fetch, join, and structure active options contracts with pricing, IV,
        and freshness flags, treating illiquid bids/asks/marks as nullable.
        """
        ...
