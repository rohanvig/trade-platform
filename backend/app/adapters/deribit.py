import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import random
from typing import Any

import httpx

from app.adapters.base import MarketDataAdapter
from app.adapters.exceptions import (
    DeribitAdapterError,
    DeribitDataError,
    DeribitRateLimitError,
    DeribitTimeoutError,
    UnsupportedAssetError,
)
from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoQuote,
    OptionContractSummary,
)


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        f = float(val)
        if f <= 0:
            return None
        return Decimal(str(val))
    except (ValueError, TypeError):
        return None


def _require_decimal(val: Any, default: str = "0") -> Decimal:
    if val is None:
        return Decimal(default)
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (ValueError, TypeError):
        return Decimal(default)


def _convert_to_usd(
    raw_val: Decimal | None,
    settlement_currency: str,
    quote_currency: str,
    underlying: str,
    index_price: Decimal,
) -> Decimal | None:
    """
    Converts raw option price to USD based on verified exchange contract denominations.
    
    Rules:
    1. Inverse (Coin-Margined) BTC/ETH contracts:
       Premium is quoted in the underlying asset (BTC or ETH).
       USD = raw_price * underlying_index_price
    2. Linear USDC contracts:
       Premium is quoted directly in USD or USDC (1:1 USD peg).
       USD = raw_price
    3. Unverified / Unsupported currency pairings:
       Returns None rather than guessing or fabricating an unverified valuation.
    """
    if raw_val is None:
        return None

    settle = settlement_currency.upper()
    quote = quote_currency.upper()
    und = underlying.upper()

    # Case 1: Coin-margined inverse contracts (BTC options in BTC, ETH options in ETH)
    if und in ("BTC", "ETH") and settle == und and quote == und:
        return raw_val * index_price

    # Case 2: Linear contracts settled in USDC and quoted in USD or USDC
    if settle == "USDC" and quote in ("USDC", "USD"):
        return raw_val
    if quote in ("USD", "USDC") and settle in ("USD", "USDC"):
        return raw_val

    # Case 3: Deribit options with underlying BTC/ETH settled in USDC
    if und in ("BTC", "ETH") and quote in ("USD", "USDC") and settle == "USDC":
        return raw_val

    # Unverified denomination -> return null rather than inventing a value
    return None


class DeribitMarketDataAdapter(MarketDataAdapter):
    """
    Asynchronous unauthenticated adapter for Deribit API v2 public endpoints.
    Handles rate limiting, exponential backoff with jitter, metadata joins,
    and strict string-based Decimal conversion.
    """

    SUPPORTED_ASSETS = ("BTC", "ETH")

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str = "https://www.deribit.com/api/v2/public",
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        max_retries: int = 3,
        base_backoff: float = 0.25,
        max_backoff: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            headers={"User-Agent": "TradePilot-Workstation/1.0"},
        )

    async def close(self) -> None:
        """Close internal HTTP client if owned."""
        if not self._external_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "DeribitMarketDataAdapter":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _validate_underlying(self, underlying: str) -> str:
        asset = underlying.strip().upper()
        if asset not in self.SUPPORTED_ASSETS:
            raise UnsupportedAssetError(
                f"Unsupported asset '{underlying}'. TradePilot only supports {list(self.SUPPORTED_ASSETS)}."
            )
        return asset

    async def _request(
        self,
        method_name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{method_name}"

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url, params=params)

                if response.status_code in (429, 503):
                    if attempt == self.max_retries:
                        raise DeribitRateLimitError(
                            f"Deribit rate limit exceeded on {method_name} (HTTP {response.status_code}) after {self.max_retries} retries"
                        )
                    jitter = random.uniform(0.0, 0.1) if self.base_backoff > 0 else 0.0
                    backoff = min(self.max_backoff, self.base_backoff * (2**attempt) + jitter)
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    raise DeribitDataError(
                        f"HTTP error {response.status_code} from {method_name}: {response.text}"
                    )

                try:
                    data = response.json()
                except Exception as exc:
                    raise DeribitDataError(
                        f"Failed to decode JSON from {method_name}: {exc}"
                    ) from exc

                if not isinstance(data, dict):
                    raise DeribitDataError(
                        f"Malformed response payload from {method_name}: expected dict, got {type(data)}"
                    )

                # Check JSON-RPC error structure
                if "error" in data:
                    err = data["error"]
                    err_code = err.get("code") if isinstance(err, dict) else None
                    err_msg = str(err.get("message") if isinstance(err, dict) else err)
                    if err_code == 10028 or "too_many_requests" in err_msg.lower():
                        if attempt == self.max_retries:
                            raise DeribitRateLimitError(
                                f"Deribit JSON-RPC rate limit exceeded on {method_name}: {err_msg}"
                            )
                        jitter = random.uniform(0.0, 0.1) if self.base_backoff > 0 else 0.0
                        backoff = min(self.max_backoff, self.base_backoff * (2**attempt) + jitter)
                        await asyncio.sleep(backoff)
                        continue
                    raise DeribitDataError(f"Deribit JSON-RPC error from {method_name}: {err}")

                if "result" not in data:
                    raise DeribitDataError(
                        f"Missing 'result' attribute in response from {method_name}"
                    )

                return data["result"]

            except httpx.TimeoutException as exc:
                if attempt == self.max_retries:
                    raise DeribitTimeoutError(
                        f"Timeout connecting to Deribit {method_name}: {exc}"
                    ) from exc
                jitter = random.uniform(0.0, 0.1) if self.base_backoff > 0 else 0.0
                backoff = min(self.max_backoff, self.base_backoff * (2**attempt) + jitter)
                await asyncio.sleep(backoff)
            except (DeribitAdapterError, httpx.HTTPError):
                raise
            except Exception as exc:
                raise DeribitDataError(
                    f"Unexpected error communicating with Deribit {method_name}: {exc}"
                ) from exc

        raise DeribitRateLimitError(f"Exhausted retries for {method_name}")

    async def get_index_price(self, underlying: str) -> CryptoQuote:
        """
        Fetch current reference spot index price for the given asset (BTC or ETH).
        Explicitly marked with is_index=True.
        """
        asset = self._validate_underlying(underlying)
        index_name = "btc_usd" if asset == "BTC" else "eth_usd"

        result = await self._request("get_index_price", {"index_name": index_name})
        if not isinstance(result, dict) or "index_price" not in result:
            raise DeribitDataError(
                f"Invalid index price payload for {index_name}: {result}"
            )

        index_price_raw = result["index_price"]
        est_deliv_raw = result.get("estimated_delivery_price")

        return CryptoQuote(
            underlying=asset,
            index_name=index_name,
            index_price=Decimal(str(index_price_raw)),
            estimated_delivery_price=(
                Decimal(str(est_deliv_raw)) if est_deliv_raw is not None else None
            ),
            is_index=True,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_instrument_candles(
        self,
        instrument_name: str,
        resolution: str,
        start_ts: int,
        end_ts: int,
    ) -> list[CryptoCandle]:
        """
        Fetch historical traded instrument OHLCV candles (e.g. BTC-PERPETUAL) from TradingView chart data.
        """
        res_map = {
            "1h": "60",
            "60": "60",
            "1d": "1D",
            "1D": "1D",
            "4h": "240",
            "240": "240",
        }
        api_resolution = res_map.get(resolution, resolution)

        result = await self._request(
            "get_tradingview_chart_data",
            {
                "instrument_name": instrument_name,
                "start_timestamp": start_ts,
                "end_timestamp": end_ts,
                "resolution": api_resolution,
            },
        )

        if not isinstance(result, dict) or result.get("status") != "ok":
            return []

        ticks = result.get("ticks", [])
        opens = result.get("open", [])
        highs = result.get("high", [])
        lows = result.get("low", [])
        closes = result.get("close", [])
        volumes = result.get("volume", [])

        count = len(ticks)
        if not (count == len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)):
            raise DeribitDataError(
                f"Mismatched array lengths in chart data for {instrument_name}"
            )

        timeframe_label = "1h" if api_resolution == "60" else ("1d" if api_resolution == "1D" else resolution)

        candles: list[CryptoCandle] = []
        for i in range(count):
            dt = datetime.fromtimestamp(ticks[i] / 1000.0, tz=timezone.utc)
            candles.append(
                CryptoCandle(
                    instrument_name=instrument_name,
                    timeframe=timeframe_label,
                    timestamp=dt,
                    open=Decimal(str(opens[i])),
                    high=Decimal(str(highs[i])),
                    low=Decimal(str(lows[i])),
                    close=Decimal(str(closes[i])),
                    volume=Decimal(str(volumes[i])),
                    is_closed=True,
                )
            )

        return candles

    async def get_active_instruments(self, currency: str) -> list[dict[str, Any]]:
        """
        Fetch active instrument definitions for a currency (BTC, ETH),
        filtering strictly for state="open" per the approved specification.
        """
        asset = self._validate_underlying(currency)
        result = await self._request(
            "get_instruments",
            {
                "currency": asset,
                "kind": "option",
                "expired": "false",
            },
        )

        if not isinstance(result, list):
            raise DeribitDataError(
                f"Expected list of instruments for {currency}, got {type(result)}"
            )

        active = [
            inst
            for inst in result
            if isinstance(inst, dict) and inst.get("state") == "open"
        ]
        return active

    async def get_book_summary(self, currency: str) -> list[dict[str, Any]]:
        """
        Fetch current book summary across all option contracts for a currency.
        """
        asset = self._validate_underlying(currency)
        result = await self._request(
            "get_book_summary_by_currency",
            {
                "currency": asset,
                "kind": "option",
            },
        )

        if not isinstance(result, list):
            raise DeribitDataError(
                f"Expected list of book summaries for {currency}, got {type(result)}"
            )

        return [item for item in result if isinstance(item, dict)]

    async def get_options_chain(
        self,
        underlying: str,
        expiry_date: date | None = None,
    ) -> list[OptionContractSummary]:
        """
        Fetch, join, and structure active options contracts with pricing, IV,
        and freshness flags, treating illiquid bids/asks/marks as nullable.
        """
        asset = self._validate_underlying(underlying)

        # Retrieve active instruments, book summary, and underlying index price concurrently
        instruments, book_summaries, index_quote = await asyncio.gather(
            self.get_active_instruments(asset),
            self.get_book_summary(asset),
            self.get_index_price(asset),
        )

        book_map = {
            b["instrument_name"]: b
            for b in book_summaries
            if "instrument_name" in b
        }

        contracts: list[OptionContractSummary] = []
        underlying_price = index_quote.index_price

        for inst in instruments:
            name = inst.get("instrument_name")
            if not name:
                continue

            exp_ts = inst.get("expiration_timestamp")
            if not exp_ts:
                continue

            contract_expiry = datetime.fromtimestamp(exp_ts / 1000.0, tz=timezone.utc).date()
            if expiry_date and contract_expiry != expiry_date:
                continue

            strike_raw = inst.get("strike")
            if strike_raw is None:
                continue
            strike = Decimal(str(strike_raw))

            option_type_raw = inst.get("option_type", "")
            option_type = "CALL" if option_type_raw.lower() == "call" or name.endswith("-C") else "PUT"

            settlement_currency = str(inst.get("settlement_currency") or asset).upper()
            quote_currency = str(inst.get("quote_currency") or settlement_currency).upper()
            contract_size = _require_decimal(inst.get("contract_size", 1.0), "1.0")

            book = book_map.get(name, {})
            mark_price_raw = _to_decimal(book.get("mark_price"))
            mark_iv = _to_decimal(book.get("mark_iv"))
            bid_price_raw = _to_decimal(book.get("bid_price"))
            ask_price_raw = _to_decimal(book.get("ask_price"))
            open_interest = _require_decimal(book.get("open_interest"), "0")
            volume_usd = _require_decimal(book.get("volume_usd"), "0")

            # USD conversion strictly using verified contract denomination
            mark_price_usd = _convert_to_usd(
                mark_price_raw, settlement_currency, quote_currency, asset, underlying_price
            )
            bid_price_usd = _convert_to_usd(
                bid_price_raw, settlement_currency, quote_currency, asset, underlying_price
            )
            ask_price_usd = _convert_to_usd(
                ask_price_raw, settlement_currency, quote_currency, asset, underlying_price
            )

            contract = OptionContractSummary(
                instrument_name=name,
                underlying=asset,
                strike=strike,
                option_type=option_type,
                expiry_date=contract_expiry,
                expiration_timestamp=int(exp_ts),
                contract_size=contract_size,
                settlement_currency=settlement_currency,
                quote_currency=quote_currency,
                mark_price_raw=mark_price_raw,
                mark_price_usd=mark_price_usd,
                mark_iv=mark_iv,
                bid_price_raw=bid_price_raw,
                ask_price_raw=ask_price_raw,
                bid_price_usd=bid_price_usd,
                ask_price_usd=ask_price_usd,
                open_interest=open_interest,
                is_oi_delayed=True,
                volume_usd=volume_usd,
            )
            contracts.append(contract)

        contracts.sort(key=lambda c: (c.expiry_date, c.strike, c.option_type))
        return contracts

