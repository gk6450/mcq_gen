import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import ssl as _ssl
from app.logger import get_logger

load_dotenv()
logger = get_logger()

RAW_DATABASE_URL = os.getenv("DATABASE_URL")

logger.info("Raw DATABASE_URL detected (masked for logs)")

# Parse URL and translate sslmode (if present) into asyncpg-compatible connect_args
_parsed = urlparse(RAW_DATABASE_URL)
_qs = parse_qs(_parsed.query)

connect_args = {}
# handle sslmode if provided in the URL query string (e.g. ?sslmode=disable / require)
if "sslmode" in _qs:
    sslmode = _qs.pop("sslmode")[0].lower()
    logger.info("Detected sslmode=%s in DATABASE_URL - translating for asyncpg", sslmode)
    # map sslmode to asyncpg 'ssl' parameter
    if sslmode in ("disable", "allow", "prefer"):
        connect_args["ssl"] = False
    else:
        ctx = _ssl.create_default_context()
        connect_args["ssl"] = ctx

    # rebuild URL without sslmode parameter
    new_qs = urlencode({k: v[0] for k, v in _qs.items()})
    DATABASE_URL = urlunparse(_parsed._replace(query=new_qs))
else:
    DATABASE_URL = RAW_DATABASE_URL

logger.debug("Final DATABASE_URL used for engine creation (masked): %s", DATABASE_URL.replace("://", "://***"))

# Create async engine. Pass connect_args only if not empty to avoid unexpected kwargs.
if connect_args:
    engine = create_async_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
    logger.info("Created async SQLAlchemy engine with custom connect_args")
else:
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    logger.info("Created async SQLAlchemy engine")

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
