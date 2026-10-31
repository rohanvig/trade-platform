import numpy as np
import pandas as pd
import pytest

from app.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)


# ==============================================================================
# Unit Tests for Indicator Math Calculations
# ==============================================================================


def test_sma_calculation():
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma = calculate_sma(prices, period=3)

    assert pd.isna(sma.iloc[0])
    assert pd.isna(sma.iloc[1])
    assert sma.iloc[2] == pytest.approx(20.0)  # (10 + 20 + 30) / 3
    assert sma.iloc[3] == pytest.approx(30.0)  # (20 + 30 + 40) / 3
    assert sma.iloc[4] == pytest.approx(40.0)  # (30 + 40 + 50) / 3


def test_sma_invalid_period():
    prices = pd.Series([10.0, 20.0])
    with pytest.raises(ValueError):
        calculate_sma(prices, period=0)
    with pytest.raises(ValueError):
        calculate_sma(prices, period=5)  # Series shorter than period


def test_ema_calculation():
    prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    ema = calculate_ema(prices, period=3)
    assert not pd.isna(ema.iloc[-1])
    # EMA weights recent prices more than SMA
    assert ema.iloc[-1] > calculate_sma(prices, period=3).iloc[-1] - 1.0


def test_rsi_extremes():
    # Continually rising prices should push RSI to 100
    rising = pd.Series([float(i) for i in range(1, 30)])
    rsi_rising = calculate_rsi(rising, period=14)
    assert rsi_rising.iloc[-1] == pytest.approx(100.0, abs=0.1)

    # Continually falling prices should push RSI to 0
    falling = pd.Series([float(100 - i) for i in range(30)])
    rsi_falling = calculate_rsi(falling, period=14)
    assert rsi_falling.iloc[-1] == pytest.approx(0.0, abs=0.1)


def test_rsi_bounded_range():
    np.random.seed(42)
    random_walk = pd.Series(np.cumsum(np.random.randn(50)) + 100)
    rsi = calculate_rsi(random_walk, period=14)
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0.0).all()
    assert (valid_rsi <= 100.0).all()


def test_macd_calculation():
    np.random.seed(42)
    prices = pd.Series(np.cumsum(np.random.randn(60)) + 100)
    macd_df = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    assert "macd" in macd_df.columns
    assert "signal" in macd_df.columns
    assert "histogram" in macd_df.columns

    # Verify histogram = macd - signal
    diff = macd_df["macd"] - macd_df["signal"]
    assert np.allclose(macd_df["histogram"].dropna(), diff.dropna())


def test_macd_invalid_periods():
    prices = pd.Series(range(50), dtype=float)
    with pytest.raises(ValueError):
        calculate_macd(prices, fast_period=26, slow_period=12)  # fast >= slow


def test_bollinger_bands():
    prices = pd.Series([10.0 + (i % 5) for i in range(30)])
    bb = calculate_bollinger_bands(prices, period=20, std_multiplier=2.0)

    assert "upper" in bb.columns
    assert "middle" in bb.columns
    assert "lower" in bb.columns

    valid = bb.dropna()
    assert (valid["upper"] >= valid["middle"]).all()
    assert (valid["middle"] >= valid["lower"]).all()


def test_atr_calculation():
    high = pd.Series([12.0, 13.0, 14.0, 13.5, 15.0] * 5)
    low = pd.Series([10.0, 11.0, 11.5, 12.0, 13.0] * 5)
    close = pd.Series([11.0, 12.0, 13.0, 12.5, 14.0] * 5)

    atr = calculate_atr(high, low, close, period=14)
    valid_atr = atr.dropna()
    assert len(valid_atr) > 0
    assert (valid_atr > 0).all()


def test_vwap_calculation():
    high = pd.Series([11.0, 12.0, 13.0])
    low = pd.Series([9.0, 10.0, 11.0])
    close = pd.Series([10.0, 11.0, 12.0])
    volume = pd.Series([100, 100, 100])

    vwap = calculate_vwap(high, low, close, volume)
    # Typical prices: 10.0, 11.0, 12.0 with equal volumes
    assert vwap.iloc[0] == pytest.approx(10.0)
    assert vwap.iloc[1] == pytest.approx(10.5)  # (1000 + 1100) / 200 = 10.5
    assert vwap.iloc[2] == pytest.approx(11.0)  # (1000 + 1100 + 1200) / 300 = 11.0


# ==============================================================================
# Integration Tests for Indicator Endpoints
# ==============================================================================


def test_api_get_sma(client):
    response = client.get("/api/v1/indicators/sma?symbol=AAPL&period=10&period_range=1mo")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "SMA"
    assert len(data["points"]) > 0


def test_api_get_rsi(client):
    response = client.get("/api/v1/indicators/rsi?symbol=AAPL&period=14&period_range=3mo")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "RSI"
    points = [p["value"] for p in data["points"] if p["value"] is not None]
    assert len(points) > 0
    assert all(0.0 <= p <= 100.0 for p in points)


def test_api_get_macd(client):
    response = client.get("/api/v1/indicators/macd?symbol=AAPL&fast_period=12&slow_period=26")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "MACD"
    assert len(data["points"]) > 0


def test_api_get_bollinger(client):
    response = client.get("/api/v1/indicators/bollinger?symbol=AAPL&period=20")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "BOLLINGER_BANDS"
    assert len(data["points"]) > 0


def test_api_get_atr(client):
    response = client.get("/api/v1/indicators/atr?symbol=AAPL&period=14")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "ATR"


def test_api_get_vwap(client):
    response = client.get("/api/v1/indicators/vwap?symbol=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["indicator"] == "VWAP"


def test_api_indicator_invalid_symbol(client):
    response = client.get("/api/v1/indicators/sma?symbol=XYZQWERTY999")
    assert response.status_code == 400
