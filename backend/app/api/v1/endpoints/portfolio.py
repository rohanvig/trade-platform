from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioResponse, PositionResponse
from app.services.portfolio import PortfolioService

router = APIRouter(
    prefix="/portfolio",
    tags=["Paper Trading & Portfolio"],
)


@router.get(
    "",
    response_model=PortfolioResponse,
    summary="Get user paper trading portfolio summary with live unrealized PnL",
)
def get_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PortfolioService(db)
    return service.get_portfolio_summary(current_user.id)


@router.get(
    "/positions",
    response_model=list[PositionResponse],
    summary="Get user current open positions",
)
def get_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PortfolioService(db)
    summary = service.get_portfolio_summary(current_user.id)
    return summary.positions
