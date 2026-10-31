from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from app.strategies.base import SignalType
from app.strategies.macd_crossover import MACDCrossoverStrategy
from app.strategies.registry import get_strategy, list_strategies
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.strategies.sma_crossover import SMACrossoverStrategy


# ==============================================================================
# Helper to create synthetic OHLCV DataFrame
# ==============================================================================


def create_synthetic_df(prices: list[float]) -> pd.DataFrame:
    dates = pd.date_range(start="2026-01-01", periods=len(prices), freq="D")
    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p * 1.02 for p in prices],
            "Low": [p * 0.98 for p in prices],
            "Close": prices,
            "Volume": [100000] * len(prices),
        },
        index=dates,
    )


# ==============================================================================
# Strategy Unit Tests
# ==============================================================================


def test_sma_crossover_signals():
    # Prices: flat, then drop (death cross), then jump (golden cross)
    prices = [50.0] * 15 + [40.0] * 10 + [60.0] * 15
    df = create_synthetic_df(prices)

    strategy = SMACrossoverStrategy(fast_period=5, slow_period=10, stop_loss_pct=2.0, take_profit_pct=5.0)
    signals = strategy.generate_signals(df, symbol="TEST")

    assert len(signals) > 0
    first_signal = signals[0]
    assert first_signal.symbol == "TEST"
    assert first_signal.signal in (SignalType.BUY, SignalType.SELL)
    assert first_signal.stop_loss is not None
    assert first_signal.take_profit is not None

    if first_signal.signal == SignalType.BUY:
        assert first_signal.stop_loss < first_signal.price
        assert first_signal.take_profit > first_signal.price
    elif first_signal.signal == SignalType.SELL:
        assert first_signal.stop_loss > first_signal.price
        assert first_signal.take_profit < first_signal.price


def test_rsi_mean_reversion_signals():
    # Continual drop to oversold (<30), then continual climb to overbought (>70)
    prices = [100.0 - i * 3.0 for i in range(18)] + [50.0 + i * 4.0 for i in range(25)]
    df = create_synthetic_df(prices)

    strategy = RSIMeanReversionStrategy(period=14, oversold_threshold=30.0, overbought_threshold=70.0)
    signals = strategy.generate_signals(df, symbol="TEST")

    assert len(signals) >= 1
    # Check that signals include oversold buy
    has_buy = any(s.signal == SignalType.BUY for s in signals)
    assert has_buy


def test_macd_crossover_signals():
    np.random.seed(123)
    prices = list(np.cumsum(np.random.randn(60)) + 100)
    df = create_synthetic_df(prices)

    strategy = MACDCrossoverStrategy(fast_period=12, slow_period=26, signal_period=9)
    signals = strategy.generate_signals(df, symbol="TEST")

    # Should detect crossovers over a 60-bar random walk
    assert isinstance(signals, list)
    for s in signals:
        assert s.signal in (SignalType.BUY, SignalType.SELL)
        assert "macd" in s.metadata
        assert "signal" in s.metadata


def test_strategy_registry():
    strategies = list_strategies()
    assert len(strategies) >= 3
    names = [s["name"] for s in strategies]
    assert "SMA_CROSSOVER" in names
    assert "RSI_MEAN_REVERSION" in names
    assert "MACD_CROSSOVER" in names

    strat = get_strategy("SMA_CROSSOVER", fast_period=5, slow_period=15)
    assert strat.name == "SMA_CROSSOVER"
    assert strat.params["fast_period"] == 5

    with pytest.raises(ValueError):
        get_strategy("NON_EXISTENT_STRATEGY")


# ==============================================================================
# Strategy API Integration Tests
# ==============================================================================


def test_api_list_strategies(client):
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(s["name"] == "SMA_CROSSOVER" for s in data)


def test_api_run_strategy_success(client):
    payload = {
        "symbol": "AAPL",
        "strategy_name": "SMA_CROSSOVER",
        "params": {
            "fast_period": 10,
            "slow_period": 20,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0,
        },
        "timeframe": "1d",
        "period_range": "6mo",
    }
    response = client.post("/api/v1/strategies/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["strategy_name"] == "SMA_CROSSOVER"
    assert "total_signals" in data
    assert "signals" in data


def test_api_run_strategy_invalid_name(client):
    payload = {
        "symbol": "AAPL",
        "strategy_name": "DOES_NOT_EXIST",
    }
    response = client.post("/api/v1/strategies/run", json=payload)
    assert response.status_code == 400
    assert "Unknown strategy" in response.json()["detail"]
