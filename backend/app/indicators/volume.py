import pandas as pd


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Calculate Volume-Weighted Average Price (VWAP) from scratch.
    Typical Price (TP) = (High + Low + Close) / 3
    VWAP = cumsum(TP * Volume) / cumsum(Volume)
    """
    if len(close) == 0:
        raise ValueError("Series cannot be empty")
    if volume.sum() == 0:
        raise ValueError("Cumulative volume cannot be zero")

    typical_price = (high + low + close) / 3.0
    cum_pv = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()

    vwap = cum_pv / cum_vol
    vwap.name = "vwap"
    return vwap
