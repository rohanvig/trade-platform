from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from sqlalchemy import text

from app.db.database import engine
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="trial purposes"
)
app.include_router(api_router)