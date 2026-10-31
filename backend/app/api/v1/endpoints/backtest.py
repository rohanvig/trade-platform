from fastapi import APIRouter, HTTPException, status

from app.schemas.backtest import BacktestRequest, BacktestResponse
from app.services.backtest import BacktestService

router = APIRouter(
    prefix="/backtest",
    tags=["Backtesting Engine"],
)

backtest_service = BacktestService()


@router.post(
    "/run",
    response_model=BacktestResponse,
    summary="Run an algorithmic strategy backtest over historical market data with equity curve and trade analytics",
)
def run_backtest(request: BacktestRequest):
    try:
        return backtest_service.run_backtest(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
