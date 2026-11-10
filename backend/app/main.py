from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from app.adapters.deribit import DeribitMarketDataAdapter
from app.api.router import api_router
from app.core.config import settings
from app.services.crypto_market import CryptoMarketDataService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize single shared httpx.AsyncClient
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "TradePilot-Workstation/1.0"},
    )
    adapter = DeribitMarketDataAdapter(client=http_client)
    service = CryptoMarketDataService(adapter=adapter)

    app.state.http_client = http_client
    app.state.crypto_adapter = adapter
    app.state.crypto_service = service

    yield

    # Gracefully close single shared httpx.AsyncClient on shutdown
    if not http_client.is_closed:
        await http_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="TradePilot Algorithmic Trading API",
    lifespan=lifespan,
)

# CORS configuration
origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(api_router)