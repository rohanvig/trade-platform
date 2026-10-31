from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.market import (
    HistoricalDataResponse,
    QuoteResponse,
    SymbolSearchResult,
)
from app.services.market import MarketDataService

router = APIRouter(
    prefix="/market",
    tags=["Market Data"],
)

market_service = MarketDataService()


@router.get(
    "/quote",
    response_model=QuoteResponse,
    summary="Get real-time / current market quote",
)
def get_quote(
    symbol: str = Query(..., min_length=1, max_length=20, description="Ticker symbol (e.g. AAPL, TSLA, BTC-USD)"),
):
    try:
        return market_service.get_quote(symbol)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/history",
    response_model=HistoricalDataResponse,
    summary="Get historical OHLCV bars",
)
def get_history(
    symbol: str = Query(..., min_length=1, max_length=20, description="Ticker symbol"),
    timeframe: str = Query(default="1d", description="Bar interval: 1m, 5m, 15m, 1h, 1d, 1wk"),
    period: str = Query(default="1mo", description="Historical range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
):
    try:
        return market_service.get_history(
            symbol=symbol,
            timeframe=timeframe,
            period=period,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/search",
    response_model=list[SymbolSearchResult],
    summary="Search for symbols and company names",
)
def search_symbols(
    query: str = Query(..., min_length=1, max_length=50, description="Search term or ticker prefix"),
):
    return market_service.search_symbols(query)
