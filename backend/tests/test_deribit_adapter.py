import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
import json

import httpx
import pytest

from app.adapters.base import MarketDataAdapter
from app.adapters.deribit import DeribitMarketDataAdapter
from app.adapters.exceptions import (
    DeribitDataError,
    DeribitRateLimitError,
    DeribitTimeoutError,
    UnsupportedAssetError,
)
from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoQuote,
    OptionChainResponse,
    OptionContractSummary,
)


def test_crypto_quote_schema_invariants():
    """Verify CryptoQuote financial precision and is_index flag."""
    quote = CryptoQuote(
        underlying="BTC",
        index_name="btc_usd",
        index_price=68435.12,  # Float input to test strict string Decimal conversion
        estimated_delivery_price=68420.50,
        is_index=True,
        timestamp=datetime.now(timezone.utc),
    )
    assert quote.is_index is True
    assert isinstance(quote.index_price, Decimal)
    assert quote.index_price == Decimal("68435.12")
    assert quote.estimated_delivery_price == Decimal("68420.5")


def test_option_contract_summary_schema_invariants():
    """Verify OptionContractSummary float invariance, nullable quotes, and option type normalization."""
    # AC-007: Ingesting float 0.045 converts to exact Decimal("0.045")
    contract = OptionContractSummary(
        instrument_name="BTC-27DEC26-100000-C",
        underlying="BTC",
        strike=100000.0,
        option_type="call",
        expiry_date=date(2026, 12, 27),
        expiration_timestamp=1798358400000,
        contract_size=1.0,
        settlement_currency="BTC",
        quote_currency="USD",
        mark_price_raw=0.045,
        mark_price_usd=3079.58,
        mark_iv=62.4,
        bid_price_raw=None,  # Nullable quote
        ask_price_raw=None,
        open_interest=1542.0,
        is_oi_delayed=True,
    )
    assert contract.option_type == "CALL"
    assert contract.strike == Decimal("100000.0")
    assert contract.mark_price_raw == Decimal("0.045")
    assert contract.mark_iv == Decimal("62.4")
    assert contract.bid_price_raw is None
    assert contract.ask_price_raw is None
    assert contract.is_oi_delayed is True


@pytest.mark.anyio
async def test_deribit_get_index_price_success():
    """AC-001: get_index_price returns CryptoQuote with is_index=True and correct Decimal price."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert "get_index_price" in str(request.url)
        assert "index_name=btc_usd" in str(request.url)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "result": {
                    "index_price": 68435.12,
                    "estimated_delivery_price": 68420.50,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        quote = await adapter.get_index_price("BTC")
        assert quote.underlying == "BTC"
        assert quote.index_name == "btc_usd"
        assert quote.is_index is True
        assert quote.index_price == Decimal("68435.12")
        assert quote.estimated_delivery_price == Decimal("68420.5")


@pytest.mark.anyio
async def test_deribit_unsupported_asset():
    """Verify requesting an unsupported asset raises UnsupportedAssetError."""
    adapter = DeribitMarketDataAdapter(base_backoff=0.0)
    with pytest.raises(UnsupportedAssetError) as exc_info:
        await adapter.get_index_price("SOL")
    assert "Unsupported asset 'SOL'" in str(exc_info.value)
    await adapter.close()


@pytest.mark.anyio
async def test_deribit_get_instrument_candles():
    """Verify get_instrument_candles parses TradingView OHLCV arrays into CryptoCandle objects."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert "get_tradingview_chart_data" in str(request.url)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "result": {
                    "status": "ok",
                    "ticks": [1700000000000, 1700003600000],
                    "open": [68000.0, 68100.0],
                    "high": [68500.0, 68600.0],
                    "low": [67900.0, 68050.0],
                    "close": [68100.0, 68400.0],
                    "volume": [120.5, 95.2],
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        candles = await adapter.get_instrument_candles("BTC-PERPETUAL", "1h", 1700000000000, 1700007200000)
        assert len(candles) == 2
        assert candles[0].instrument_name == "BTC-PERPETUAL"
        assert candles[0].timeframe == "1h"
        assert candles[0].open == Decimal("68000.0")
        assert candles[0].close == Decimal("68100.0")
        assert candles[0].volume == Decimal("120.5")
        assert candles[0].is_closed is True


@pytest.mark.anyio
async def test_deribit_active_instruments_filters_open_state():
    """
    Check 1 & AC-004: get_active_instruments filters strictly by state='open'.
    Ensures that:
    1. Instruments with state='open' are included even if is_active is omitted.
    2. Instruments with state in ('closed', 'settlement', 'locked', 'halted') are excluded.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "result": [
                    {
                        "instrument_name": "BTC-27DEC26-100000-C",
                        "strike": 100000.0,
                        "state": "open",
                        # is_active intentionally omitted to verify state='open' is sovereign
                    },
                    {
                        "instrument_name": "BTC-27DEC26-95000-C",
                        "strike": 95000.0,
                        "state": "open",
                        "is_active": True,
                    },
                    {
                        "instrument_name": "BTC-27DEC26-90000-C",
                        "strike": 90000.0,
                        "state": "closed",
                    },
                    {
                        "instrument_name": "BTC-27DEC26-85000-C",
                        "strike": 85000.0,
                        "state": "settlement",
                    },
                    {
                        "instrument_name": "BTC-27DEC26-80000-C",
                        "strike": 80000.0,
                        "state": "locked",
                    },
                    {
                        "instrument_name": "BTC-27DEC26-75000-C",
                        "strike": 75000.0,
                        "state": "halted",
                    },
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        active = await adapter.get_active_instruments("BTC")
        assert len(active) == 2
        names = [item["instrument_name"] for item in active]
        assert "BTC-27DEC26-100000-C" in names
        assert "BTC-27DEC26-95000-C" in names


@pytest.mark.anyio
async def test_deribit_options_chain_nullable_quotes_and_btc_inverse_conversion():
    """
    Check 2 (Inverse BTC):
    - Preserves raw prices in BTC quote_currency.
    - Accurately converts mark_price_usd = mark_price_raw * index_price.
    - AC-005: Nullable quotes retained with None.
    - AC-006: Open interest marked with is_oi_delayed=True.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "get_instruments" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC-27DEC26-100000-C",
                            "strike": 100000.0,
                            "option_type": "call",
                            "expiration_timestamp": 1798358400000,
                            "contract_size": 1.0,
                            "settlement_currency": "BTC",
                            "quote_currency": "BTC",
                            "state": "open",
                        },
                        {
                            "instrument_name": "BTC-27DEC26-150000-C",
                            "strike": 150000.0,
                            "option_type": "call",
                            "expiration_timestamp": 1798358400000,
                            "contract_size": 1.0,
                            "settlement_currency": "BTC",
                            "quote_currency": "BTC",
                            "state": "open",
                        },
                    ],
                },
            )
        elif "get_book_summary_by_currency" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC-27DEC26-100000-C",
                            "mark_price": 0.045,
                            "bid_price": 0.043,
                            "ask_price": 0.047,
                            "mark_iv": 62.4,
                            "open_interest": 1542.0,
                        },
                        # BTC-27DEC26-150000-C is illiquid: no book entry / null values
                    ],
                },
            )
        elif "get_index_price" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"index_price": 60000.0},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        chain = await adapter.get_options_chain("BTC", expiry_date=date(2026, 12, 27))
        assert len(chain) == 2

        # First contract (Liquid with quotes in BTC)
        c1 = chain[0]
        assert c1.instrument_name == "BTC-27DEC26-100000-C"
        assert c1.settlement_currency == "BTC"
        assert c1.quote_currency == "BTC"
        assert c1.mark_price_raw == Decimal("0.045")
        # 0.045 BTC * 60000 USD/BTC = 2700 USD
        assert c1.mark_price_usd == Decimal("2700.000")
        assert c1.bid_price_raw == Decimal("0.043")
        assert c1.bid_price_usd == Decimal("2580.000")
        assert c1.ask_price_raw == Decimal("0.047")
        assert c1.ask_price_usd == Decimal("2820.000")
        assert c1.is_oi_delayed is True

        # Second contract (Illiquid with null quotes - AC-005)
        c2 = chain[1]
        assert c2.instrument_name == "BTC-27DEC26-150000-C"
        assert c2.mark_price_raw is None
        assert c2.mark_price_usd is None
        assert c2.bid_price_raw is None
        assert c2.bid_price_usd is None
        assert c2.ask_price_raw is None
        assert c2.ask_price_usd is None
        assert c2.is_oi_delayed is True


@pytest.mark.anyio
async def test_deribit_options_chain_eth_inverse_conversion():
    """
    Check 2 (Inverse ETH):
    Verifies ETH coin-margined option conversion: raw_price (in ETH) * eth_usd index.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "get_instruments" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "ETH-27DEC26-3000-C",
                            "strike": 3000.0,
                            "option_type": "call",
                            "expiration_timestamp": 1798358400000,
                            "contract_size": 1.0,
                            "settlement_currency": "ETH",
                            "quote_currency": "ETH",
                            "state": "open",
                        }
                    ],
                },
            )
        elif "get_book_summary_by_currency" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "ETH-27DEC26-3000-C",
                            "mark_price": 0.05,
                            "bid_price": 0.048,
                            "ask_price": 0.052,
                            "mark_iv": 68.0,
                            "open_interest": 500.0,
                        }
                    ],
                },
            )
        elif "get_index_price" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"index_price": 3000.0},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        chain = await adapter.get_options_chain("ETH")
        assert len(chain) == 1
        c = chain[0]
        assert c.settlement_currency == "ETH"
        assert c.quote_currency == "ETH"
        assert c.mark_price_raw == Decimal("0.05")
        # 0.05 ETH * 3000 USD/ETH = 150 USD
        assert c.mark_price_usd == Decimal("150.00")
        assert c.bid_price_usd == Decimal("144.00")
        assert c.ask_price_usd == Decimal("156.00")


@pytest.mark.anyio
async def test_deribit_options_chain_usdc_linear_conversion():
    """
    Check 2 (Linear USDC):
    Verifies linear USDC option conversion: 1:1 USD peg without index multiplication.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "get_instruments" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC_USDC-27DEC26-100000-C",
                            "strike": 100000.0,
                            "option_type": "call",
                            "expiration_timestamp": 1798358400000,
                            "contract_size": 1.0,
                            "settlement_currency": "USDC",
                            "quote_currency": "USDC",
                            "state": "open",
                        }
                    ],
                },
            )
        elif "get_book_summary_by_currency" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC_USDC-27DEC26-100000-C",
                            "mark_price": 2500.0,
                            "bid_price": 2450.0,
                            "ask_price": 2550.0,
                            "mark_iv": 60.0,
                            "open_interest": 80.0,
                        }
                    ],
                },
            )
        elif "get_index_price" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"index_price": 60000.0},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        chain = await adapter.get_options_chain("BTC")
        assert len(chain) == 1
        c = chain[0]
        assert c.settlement_currency == "USDC"
        assert c.quote_currency == "USDC"
        assert c.mark_price_raw == Decimal("2500.0")
        # Linear: already in USD/USDC, so mark_price_usd equals mark_price_raw
        assert c.mark_price_usd == Decimal("2500.0")
        assert c.bid_price_usd == Decimal("2450.0")
        assert c.ask_price_usd == Decimal("2550.0")


@pytest.mark.anyio
async def test_deribit_options_chain_unverified_denomination_returns_none():
    """
    Check 2 (Unverified Currency):
    Verifies that unrecognized/unverified denominations return null (None) rather than inventing a value.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "get_instruments" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC-27DEC26-100000-C",
                            "strike": 100000.0,
                            "option_type": "call",
                            "expiration_timestamp": 1798358400000,
                            "contract_size": 1.0,
                            "settlement_currency": "EUR",  # Unsupported / unverified pairing
                            "quote_currency": "EUR",
                            "state": "open",
                        }
                    ],
                },
            )
        elif "get_book_summary_by_currency" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "instrument_name": "BTC-27DEC26-100000-C",
                            "mark_price": 2500.0,
                            "bid_price": 2400.0,
                            "ask_price": 2600.0,
                            "mark_iv": 60.0,
                            "open_interest": 10.0,
                        }
                    ],
                },
            )
        elif "get_index_price" in url_str:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"index_price": 60000.0},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        chain = await adapter.get_options_chain("BTC")
        assert len(chain) == 1
        c = chain[0]
        # Raw prices are strictly preserved
        assert c.mark_price_raw == Decimal("2500.0")
        assert c.bid_price_raw == Decimal("2400.0")
        assert c.ask_price_raw == Decimal("2600.0")
        # USD prices are null (None) because EUR conversion formula is unverified
        assert c.mark_price_usd is None
        assert c.bid_price_usd is None
        assert c.ask_price_usd is None


@pytest.mark.anyio
async def test_deribit_rate_limit_backoff_and_exhaustion():
    """AC-008: HTTP 429 triggers retries with backoff; raises DeribitRateLimitError on exhaustion."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, json={"error": "too many requests"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(
            client=client,
            max_retries=3,
            base_backoff=0.0,  # Fast test execution
        )
        with pytest.raises(DeribitRateLimitError) as exc_info:
            await adapter.get_index_price("BTC")

        # 1 initial call + 3 retries = 4 total attempts
        assert call_count == 4
        assert "Deribit rate limit exceeded" in str(exc_info.value)


@pytest.mark.anyio
async def test_deribit_timeout_handling():
    """AC-008: Timeout raises DeribitTimeoutError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(
            client=client,
            max_retries=2,
            base_backoff=0.0,
        )
        with pytest.raises(DeribitTimeoutError) as exc_info:
            await adapter.get_index_price("BTC")
        assert "Timeout connecting to Deribit" in str(exc_info.value)


@pytest.mark.anyio
async def test_deribit_malformed_response_handling():
    """AC-009: Malformed JSON or missing fields raises DeribitDataError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOT_VALID_JSON{")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = DeribitMarketDataAdapter(client=client, base_backoff=0.0)
        with pytest.raises(DeribitDataError) as exc_info:
            await adapter.get_index_price("BTC")
        assert "Failed to decode JSON" in str(exc_info.value)


def test_market_data_adapter_protocol_conformance():
    """Verify DeribitMarketDataAdapter satisfies the MarketDataAdapter Protocol."""
    adapter = DeribitMarketDataAdapter(base_backoff=0.0)
    assert isinstance(adapter, MarketDataAdapter)

