# app/database.py
import os
from dotenv import load_dotenv
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.logger import get_logger

load_dotenv()
logger = get_logger()

# Get DATABASE_URL
RAW_DATABASE_URL = os.getenv("DATABASE_URL")
if not RAW_DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Normalize async driver
DB_URL = RAW_DATABASE_URL.strip()
if DB_URL.startswith("mysql://"):
    DB_URL = DB_URL.replace("mysql://", "mysql+asyncmy://", 1)
elif DB_URL.startswith("mysql+aiomysql://"):
    logger.warning(
        "Detected mysql+aiomysql:// in DATABASE_URL; using as-is. "
        "To use asyncmy, set mysql+asyncmy://"
    )

# Build connect_args
MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10"))
MYSQL_INIT_TIMEZONE = os.getenv("MYSQL_INIT_TIMEZONE", "+05:30")

connect_args = {
    "connect_timeout": MYSQL_CONNECT_TIMEOUT,
    "init_command": f"SET time_zone = '{MYSQL_INIT_TIMEZONE}'"
}

logger.info("Connecting to database without SSL")
logger.info(
    "Configured DB session timezone init_command: SET time_zone = '%s'",
    MYSQL_INIT_TIMEZONE,
)
logger.debug("Final DATABASE_URL used (masked): %s", DB_URL.replace("://", "://***"))

# Create async engine
engine = create_async_engine(
    DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Create a session factory. Each call to SessionLocal() returns a new AsyncSession
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

# Base for declarative models
Base = declarative_base()


# FastAPI dependency — Proper session management:
# Each request will get a fresh AsyncSession and it will be closed after use.
# Use in your route functions as: async def route(db: AsyncSession = Depends(get_db))
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
