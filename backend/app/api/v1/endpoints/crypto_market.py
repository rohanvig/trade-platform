from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.exceptions import (
    DeribitAdapterError,
    DeribitDataError,
    DeribitRateLimitError,
    DeribitTimeoutError,
    UnsupportedAssetError,
)
from app.api.dependencies import get_crypto_service
from app.schemas.crypto_market import (
    CryptoCandle,
    CryptoErrorResponse,
    CryptoQuote,
    OptionChainResponse,
)
from app.services.crypto_market import CryptoMarketDataService

router = APIRouter(
    prefix="/crypto",
    tags=["Crypto Market Data"],
)


def _handle_error(exc: Exception) -> HTTPException:
    now_iso = datetime.now(timezone.utc).isoformat()
    if isinstance(exc, UnsupportedAssetError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "UNSUPPORTED_ASSET", "message": str(exc), "timestamp": now_iso},
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_PARAMETER", "message": str(exc), "timestamp": now_iso},
        )
    if isinstance(exc, DeribitRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_code": "RATE_LIMIT_EXCEEDED", "message": str(exc), "timestamp": now_iso},
        )
    if isinstance(exc, DeribitTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error_code": "UPSTREAM_TIMEOUT", "message": str(exc), "timestamp": now_iso},
        )
    if isinstance(exc, (DeribitDataError, DeribitAdapterError)):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": "UPSTREAM_PROVIDER_ERROR", "message": str(exc), "timestamp": now_iso},
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"error_code": "INTERNAL_ERROR", "message": str(exc), "timestamp": now_iso},
    )


@router.get(
    "/quote",
    response_model=CryptoQuote,
    summary="Get real-time crypto index reference quote",
    responses={
        400: {"model": CryptoErrorResponse},
        429: {"model": CryptoErrorResponse},
        502: {"model": CryptoErrorResponse},
        504: {"model": CryptoErrorResponse},
    },
)
async def get_quote(
    underlying: str = Query(..., description="Underlying asset symbol (e.g. BTC, ETH)"),
    service: CryptoMarketDataService = Depends(get_crypto_service),
) -> CryptoQuote:
    try:
        return await service.get_index_quote(underlying)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get(
    "/history",
    response_model=list[CryptoCandle],
    summary="Get crypto perpetual OHLCV candles (1h, 4h, 1d)",
    responses={
        400: {"model": CryptoErrorResponse},
        429: {"model": CryptoErrorResponse},
        502: {"model": CryptoErrorResponse},
        504: {"model": CryptoErrorResponse},
    },
)
async def get_history(
    underlying: str = Query(..., description="Underlying asset (BTC or ETH)"),
    timeframe: str = Query(default="1d", description="Timeframe interval: 1h, 4h, 1d"),
    period: str = Query(default="30d", description="Lookback window: 1d, 7d, 14d, 30d, 90d, 1y"),
    service: CryptoMarketDataService = Depends(get_crypto_service),
) -> list[CryptoCandle]:
    try:
        return await service.get_candles(underlying, timeframe=timeframe, period=period)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get(
    "/options/expiries",
    response_model=list[str],
    summary="Get active options expiration dates",
    responses={
        400: {"model": CryptoErrorResponse},
        429: {"model": CryptoErrorResponse},
        502: {"model": CryptoErrorResponse},
        504: {"model": CryptoErrorResponse},
    },
)
async def get_option_expiries(
    underlying: str = Query(..., description="Underlying asset (BTC or ETH)"),
    service: CryptoMarketDataService = Depends(get_crypto_service),
) -> list[str]:
    try:
        return await service.get_option_expiries(underlying)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get(
    "/options/chain",
    response_model=OptionChainResponse,
    summary="Get options strike ladder and chain summary",
    responses={
        400: {"model": CryptoErrorResponse},
        429: {"model": CryptoErrorResponse},
        502: {"model": CryptoErrorResponse},
        504: {"model": CryptoErrorResponse},
    },
)
async def get_options_chain(
    underlying: str = Query(..., description="Underlying asset (BTC or ETH)"),
    expiry: str | None = Query(default=None, description="Expiration date formatted as YYYY-MM-DD"),
    service: CryptoMarketDataService = Depends(get_crypto_service),
) -> OptionChainResponse:
    try:
        return await service.get_options_chain(underlying, expiry=expiry)
    except Exception as exc:
        raise _handle_error(exc) from exc

