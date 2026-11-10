from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone


def test_market_search_symbols(client):
    response = client.get("/api/v1/market/search?query=Apple")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert any(r["symbol"] == "AAPL" for r in results)


def test_market_search_uses_mock_and_avoids_network(client, mock_market):
    """Proves yfinance.Search is intercepted by mock fixture and avoids external network calls."""
    assert len(mock_market.search_calls) == 0

    # 1. Query for Apple - proves mock was invoked with proper parameters
    response = client.get("/api/v1/market/search?query=Apple")
    assert response.status_code == 200
    assert len(mock_market.search_calls) == 1
    assert mock_market.search_calls[0]["query"] == "Apple"
    assert mock_market.search_calls[0]["max_results"] == 8

    # 2. Query for custom symbol not in POPULAR_SYMBOLS to prove mock search results are returned
    mock_market.set_search_results(
        "CustomAsset",
        [
            {
                "symbol": "CUST",
                "shortname": "Custom Asset",
                "longname": "Custom Asset Inc.",
                "exchange": "NASDAQ",
                "quoteType": "EQUITY",
            }
        ],
    )
    response_custom = client.get("/api/v1/market/search?query=CustomAsset")
    assert response_custom.status_code == 200
    assert len(mock_market.search_calls) == 2
    assert mock_market.search_calls[1]["query"] == "CustomAsset"
    results_custom = response_custom.json()
    assert any(r["symbol"] == "CUST" for r in results_custom)


def test_market_quote_success(client):
    response = client.get("/api/v1/market/quote?symbol=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert "price" in data
    assert float(data["price"]) > 0


def test_market_history_success(client):
    response = client.get("/api/v1/market/history?symbol=AAPL&timeframe=1d&period=5d")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["timeframe"] == "1d"
    assert "candles" in data
    assert len(data["candles"]) > 0
    candle = data["candles"][0]
    assert "open" in candle
    assert "high" in candle
    assert "low" in candle
    assert "close" in candle
    assert "volume" in candle


def test_market_quote_invalid_symbol(client):
    response = client.get("/api/v1/market/quote?symbol=XYZQWERTY")
    assert response.status_code == 404


def test_market_quote_symbol_too_long(client):
    response = client.get("/api/v1/market/quote?symbol=VERY_LONG_INVALID_SYMBOL_EXCEEDING_LIMIT")
    assert response.status_code == 422
