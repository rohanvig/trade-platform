from fastapi import APIRouter, HTTPException, status

from app.schemas.strategy import (
    StrategyMetadata,
    StrategyRunRequest,
    StrategyRunResponse,
)
from app.services.strategy import StrategyService

router = APIRouter(
    prefix="/strategies",
    tags=["Strategy Engine"],
)

strategy_service = StrategyService()


@router.get(
    "",
    response_model=list[StrategyMetadata],
    summary="List all available algorithmic strategies",
)
def get_strategies():
    return strategy_service.get_available_strategies()


@router.post(
    "/run",
    response_model=StrategyRunResponse,
    summary="Run an algorithmic strategy to generate buy/sell signals with stop-loss and take-profit targets",
)
def run_strategy(request: StrategyRunRequest):
    try:
        return strategy_service.run_strategy(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
