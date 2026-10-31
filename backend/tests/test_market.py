from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone


def test_market_search_symbols(client):
    response = client.get("/api/v1/market/search?query=Apple")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert any(r["symbol"] == "AAPL" for r in results)


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
