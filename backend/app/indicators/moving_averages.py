import pandas as pd


def calculate_sma(series: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA) from scratch.
    Formula: SMA_t = (1/n) * sum(P_{t-i}) for i=0 to n-1.
    """
    if period <= 0:
        raise ValueError("Period must be greater than 0")
    if len(series) < period:
        raise ValueError(f"Series length ({len(series)}) is smaller than period ({period})")

    return series.rolling(window=period, min_periods=period).mean()


def calculate_ema(series: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA) from scratch.
    Multiplier alpha = 2 / (period + 1)
    EMA_t = Price_t * alpha + EMA_{t-1} * (1 - alpha)
    """
    if period <= 0:
        raise ValueError("Period must be greater than 0")
    if len(series) < period:
        raise ValueError(f"Series length ({len(series)}) is smaller than period ({period})")

    return series.ewm(span=period, adjust=False).mean()
