# app/database.py
import os
import ssl
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.logger import get_logger

load_dotenv()
logger = get_logger()

RAW_DATABASE_URL = os.getenv("DATABASE_URL")
if not RAW_DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Normalize to use asyncmy if the URL was provided as mysql://...
DB_URL = RAW_DATABASE_URL.strip()
if DB_URL.startswith("mysql://"):
    DB_URL = DB_URL.replace("mysql://", "mysql+asyncmy://", 1)
elif DB_URL.startswith("mysql+aiomysql://"):
    # user explicitly provided aiomysql; warn that asyncmy is preferred
    logger.warning("Detected mysql+aiomysql:// in DATABASE_URL; using as-is. To use asyncmy, set mysql+asyncmy://")
# otherwise leave DB_URL as-is (e.g., mysql+asyncmy:// already present)

# Build connect_args for the async driver
connect_args = {}

# Connect timeout (driver-specific; asyncmy honors 'connect_timeout')
MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10"))
connect_args["connect_timeout"] = MYSQL_CONNECT_TIMEOUT

# SSL CA file (PEM). If present, create an SSLContext that verifies server certs.
MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA")  # path to CA cert file (PEM)
if MYSQL_SSL_CA:
    ctx = ssl.create_default_context(cafile=MYSQL_SSL_CA)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    connect_args["ssl"] = ctx
    logger.info("Configured DB SSL context using MYSQL_SSL_CA=%s", MYSQL_SSL_CA)
else:
    logger.info("No MYSQL_SSL_CA provided; connecting without custom SSL context")

# Set session timezone to IST (+05:30) on every new connection
MYSQL_INIT_TIMEZONE = os.getenv("MYSQL_INIT_TIMEZONE", "+05:30")
# init_command must be a string that will run on connection
connect_args["init_command"] = f"SET time_zone = '{MYSQL_INIT_TIMEZONE}'"
logger.info("Configured DB session timezone init_command: SET time_zone = '%s'", MYSQL_INIT_TIMEZONE)

logger.debug("Final DATABASE_URL used (masked): %s", DB_URL.replace("://", "://***"))

# Create async engine (SQLAlchemy)
engine = create_async_engine(
    DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# FastAPI dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
