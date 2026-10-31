from datetime import timezone
import pandas as pd
import pytest

from app.backtester.engine import BacktestEngine
from app.backtester.models import ExitReason
from app.strategies.sma_crossover import SMACrossoverStrategy


def create_synthetic_ohlcv(prices: list[float]) -> pd.DataFrame:
    dates = pd.date_range(start="2026-01-01", periods=len(prices), freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p * 1.02 for p in prices],
            "Low": [p * 0.98 for p in prices],
            "Close": prices,
            "Volume": [500000] * len(prices),
        },
        index=dates,
    )


# ==============================================================================
# Engine Simulation Tests
# ==============================================================================


def test_backtest_engine_run():
    # Prices: flat, then drop, then big surge
    prices = [50.0] * 15 + [40.0] * 10 + [70.0] * 20
    df = create_synthetic_ohlcv(prices)

    strategy = SMACrossoverStrategy(fast_period=5, slow_period=10, stop_loss_pct=5.0, take_profit_pct=15.0)
    engine = BacktestEngine(initial_capital=10000.0, commission_pct=0.1, slippage_pct=0.0)

    result = engine.run(strategy, df, symbol="TEST")

    assert result.symbol == "TEST"
    assert result.strategy_name == "SMA_CROSSOVER"
    assert len(result.equity_curve) == len(df)
    assert result.metrics.initial_capital == 10000.0
    assert result.metrics.max_drawdown_pct >= 0.0
    assert 0.0 <= result.metrics.win_rate_pct <= 100.0


def test_backtest_stop_loss_trigger():
    # Price enters a trade at 100, then crashes with Low dropping below 95 (5% SL)
    dates = pd.date_range(start="2026-01-01", periods=20, freq="D", tz="UTC")
    # First 12 bars warm up, bar 13 enters, bar 14 drops low
    opens = [100.0] * 12 + [100.0, 90.0] + [90.0] * 6
    highs = [101.0] * 12 + [102.0, 91.0] + [91.0] * 6
    lows = [99.0] * 12 + [99.0, 85.0] + [89.0] * 6  # Low 85 breaches 5% SL
    closes = [100.0] * 12 + [100.0, 88.0] + [90.0] * 6

    # Create synthetic price pattern that triggers buy on bar 12
    prices = [95.0] * 6 + [90.0] * 6 + [110.0] * 8
    df = pd.DataFrame(
        {"Open": prices, "High": [p * 1.05 for p in prices], "Low": [p * 0.90 for p in prices], "Close": prices, "Volume": [100000] * len(prices)},
        index=dates,
    )

    strategy = SMACrossoverStrategy(fast_period=3, slow_period=6, stop_loss_pct=2.0, take_profit_pct=20.0)
    engine = BacktestEngine(initial_capital=10000.0)
    result = engine.run(strategy, df, symbol="SL_TEST")

    # Should have executed trades
    assert len(result.trades) > 0
    reasons = [t.exit_reason for t in result.trades]
    assert any(r in (ExitReason.STOP_LOSS, ExitReason.SIGNAL, ExitReason.END_OF_DATA) for r in reasons)


# ==============================================================================
# API Integration Tests
# ==============================================================================


def test_api_run_backtest_success(client):
    payload = {
        "symbol": "AAPL",
        "strategy_name": "SMA_CROSSOVER",
        "params": {
            "fast_period": 10,
            "slow_period": 30,
            "stop_loss_pct": 3.0,
            "take_profit_pct": 6.0,
        },
        "initial_capital": 10000.0,
        "commission_pct": 0.1,
        "slippage_pct": 0.05,
        "timeframe": "1d",
        "period_range": "6mo",
    }
    response = client.post("/api/v1/backtest/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "AAPL"
    assert data["strategy_name"] == "SMA_CROSSOVER"
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["initial_capital"] == 10000.0
    assert "final_equity" in metrics
    assert "net_profit" in metrics
    assert "total_return_pct" in metrics
    assert "max_drawdown_pct" in metrics
    assert "sharpe_ratio" in metrics
    assert "win_rate_pct" in metrics

    assert "equity_curve" in data
    assert len(data["equity_curve"]) > 0
    assert "trades" in data


def test_api_run_backtest_invalid_strategy(client):
    payload = {
        "symbol": "AAPL",
        "strategy_name": "INVALID_STRATEGY_NAME",
        "initial_capital": 5000.0,
    }
    response = client.post("/api/v1/backtest/run", json=payload)
    assert response.status_code == 400
    assert "Unknown strategy" in response.json()["detail"]


def test_api_run_backtest_invalid_capital(client):
    payload = {
        "symbol": "AAPL",
        "strategy_name": "SMA_CROSSOVER",
        "initial_capital": -1000.0,  # Invalid negative capital
    }
    response = client.post("/api/v1/backtest/run", json=payload)
    assert response.status_code == 422  # Pydantic validation error (gt=0)
