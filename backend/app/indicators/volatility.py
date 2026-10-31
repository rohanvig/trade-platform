import pandas as pd

from app.indicators.moving_averages import calculate_sma


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_multiplier: float = 2.0,
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands from scratch.
    - Middle Band = SMA(period)
    - Upper Band = Middle + (std_multiplier * rolling_std)
    - Lower Band = Middle - (std_multiplier * rolling_std)
    """
    if period <= 0:
        raise ValueError("Period must be greater than 0")
    if std_multiplier <= 0:
        raise ValueError("std_multiplier must be greater than 0")
    if len(series) < period:
        raise ValueError(f"Series length ({len(series)}) must be at least period ({period})")

    middle = calculate_sma(series, period=period)
    std = series.rolling(window=period, min_periods=period).std()

    upper = middle + (std_multiplier * std)
    lower = middle - (std_multiplier * std)

    return pd.DataFrame(
        {
            "upper": upper,
            "middle": middle,
            "lower": lower,
        },
        index=series.index,
    )


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Calculate Average True Range (ATR) from scratch.
    True Range (TR) = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
    ATR = Wilder's Smoothed Average of TR over 'period'
    """
    if period <= 0:
        raise ValueError("Period must be greater than 0")
    if len(close) < period + 1:
        raise ValueError(f"Series length ({len(close)}) must be at least period + 1 ({period + 1})")

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr.name = "atr"
    return atr
