from fastapi import APIRouter

from app.api.v1.endpoints.root import router as root_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.user import router as user_router
from app.api.v1.endpoints.order import router as order_router
from app.api.v1.endpoints.market import router as market_router
from app.api.v1.endpoints.indicator import router as indicator_router
from app.api.v1.endpoints.strategy import router as strategy_router
from app.api.v1.endpoints.backtest import router as backtest_router
from app.api.v1.endpoints.portfolio import router as portfolio_router
from app.api.v1.endpoints.crypto_market import router as crypto_market_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(root_router)
api_router.include_router(health_router)
api_router.include_router(user_router)
api_router.include_router(order_router)
api_router.include_router(market_router)
api_router.include_router(indicator_router)
api_router.include_router(strategy_router)
api_router.include_router(backtest_router)
api_router.include_router(portfolio_router)
api_router.include_router(crypto_market_router)