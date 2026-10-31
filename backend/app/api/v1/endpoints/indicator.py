from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.indicator import (
    BollingerBandsResponse,
    MACDResponse,
    SingleIndicatorResponse,
)
from app.services.indicator import IndicatorService

router = APIRouter(
    prefix="/indicators",
    tags=["Technical Indicators"],
)

indicator_service = IndicatorService()


@router.get(
    "/sma",
    response_model=SingleIndicatorResponse,
    summary="Calculate Simple Moving Average (SMA)",
)
def get_sma(
    symbol: str = Query(..., min_length=1, max_length=20),
    period: int = Query(default=20, ge=1, le=500),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_sma(symbol, period, timeframe, period_range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/ema",
    response_model=SingleIndicatorResponse,
    summary="Calculate Exponential Moving Average (EMA)",
)
def get_ema(
    symbol: str = Query(..., min_length=1, max_length=20),
    period: int = Query(default=20, ge=1, le=500),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_ema(symbol, period, timeframe, period_range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/rsi",
    response_model=SingleIndicatorResponse,
    summary="Calculate Relative Strength Index (RSI)",
)
def get_rsi(
    symbol: str = Query(..., min_length=1, max_length=20),
    period: int = Query(default=14, ge=2, le=100),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_rsi(symbol, period, timeframe, period_range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/macd",
    response_model=MACDResponse,
    summary="Calculate Moving Average Convergence Divergence (MACD)",
)
def get_macd(
    symbol: str = Query(..., min_length=1, max_length=20),
    fast_period: int = Query(default=12, ge=2, le=200),
    slow_period: int = Query(default=26, ge=3, le=500),
    signal_period: int = Query(default=9, ge=1, le=100),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_macd(
            symbol, fast_period, slow_period, signal_period, timeframe, period_range
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/bollinger",
    response_model=BollingerBandsResponse,
    summary="Calculate Bollinger Bands",
)
def get_bollinger(
    symbol: str = Query(..., min_length=1, max_length=20),
    period: int = Query(default=20, ge=2, le=200),
    std_multiplier: float = Query(default=2.0, ge=0.1, le=10.0),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_bollinger_bands(
            symbol, period, std_multiplier, timeframe, period_range
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/atr",
    response_model=SingleIndicatorResponse,
    summary="Calculate Average True Range (ATR)",
)
def get_atr(
    symbol: str = Query(..., min_length=1, max_length=20),
    period: int = Query(default=14, ge=1, le=100),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="6mo"),
):
    try:
        return indicator_service.get_atr(symbol, period, timeframe, period_range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/vwap",
    response_model=SingleIndicatorResponse,
    summary="Calculate Volume-Weighted Average Price (VWAP)",
)
def get_vwap(
    symbol: str = Query(..., min_length=1, max_length=20),
    timeframe: str = Query(default="1d"),
    period_range: str = Query(default="1mo"),
):
    try:
        return indicator_service.get_vwap(symbol, timeframe, period_range)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
