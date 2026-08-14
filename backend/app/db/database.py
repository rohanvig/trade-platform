from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# Overall flow of the db connection and creation (database setup)

# FastAPI
#    ↓
# Pydantic Settings
#    ↓
# SQLAlchemy Engine
#    ↓
# Connection Pool
#    ↓
# PostgreSQL
#    ↓
# Alembic