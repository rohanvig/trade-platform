import numpy as np
import pandas as pd

from app.indicators.moving_averages import calculate_ema


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) using J. Welles Wilder's smoothing.
    Formula:
      RS = Average Gain / Average Loss
      RSI = 100 - (100 / (1 + RS))
    """
    if period <= 0:
        raise ValueError("Period must be greater than 0")
    if len(series) <= period:
        raise ValueError(f"Series length ({len(series)}) must be greater than period ({period})")

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing uses alpha = 1 / period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # Avoid division by zero
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    rsi = np.where(avg_loss == 0, 100.0, 100.0 - (100.0 / (1.0 + rs)))

    # Return as pandas Series preserving index
    rsi_series = pd.Series(rsi, index=series.index, name="rsi")
    rsi_series.iloc[:period] = np.nan  # First 'period' values are warming up
    return rsi_series


def calculate_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """
    Calculate Moving Average Convergence Divergence (MACD).
    - MACD Line: Fast EMA - Slow EMA
    - Signal Line: EMA(MACD Line, signal_period)
    - Histogram: MACD Line - Signal Line
    """
    if fast_period >= slow_period:
        raise ValueError("fast_period must be smaller than slow_period")
    if len(series) < slow_period + signal_period:
        raise ValueError(
            f"Series length ({len(series)}) is insufficient for slow_period + signal_period ({slow_period + signal_period})"
        )

    fast_ema = calculate_ema(series, period=fast_period)
    slow_ema = calculate_ema(series, period=slow_period)

    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, period=signal_period)
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        },
        index=series.index,
    )
