import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models
from .database import get_db
from dotenv import load_dotenv
import anyio
import bcrypt
from app.logger import get_logger

load_dotenv()
logger = get_logger()

SECRET_KEY = os.getenv("SECRET_KEY", "e1e05ed9a2f220bf402f174939a3ca28")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with a timezone-aware expiration timestamp.
    The 'exp' claim is stored as an integer unix timestamp (seconds).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug("Created access token for subject=%s exp=%s", data.get("sub"), int(expire.timestamp()))
    return encoded_jwt


# --- synchronous helpers (bcrypt) ---
def _hash_pw_sync(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_pw_sync(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        logger.exception("Password verification failed unexpectedly")
        return False


# --- async wrappers to avoid blocking event loop ---
async def hash_password(password: str) -> str:
    logger.debug("Hashing password (offloaded to thread)")
    return await anyio.to_thread.run_sync(_hash_pw_sync, password)


async def verify_password(plain: str, hashed: str) -> bool:
    logger.debug("Verifying password (offloaded to thread)")
    return await anyio.to_thread.run_sync(_verify_pw_sync, plain, hashed)


# --- authentication helpers (async DB) ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        logger.warning("JWT decode failed or token invalid")
        raise credentials_exception

    q = await db.execute(select(models.User).where(models.User.username == username))
    user = q.scalars().first()
    if user is None:
        logger.warning("Token valid but user not found: username=%s", username)
        raise credentials_exception
    logger.debug("Resolved current user: id=%s username=%s", user.id, user.username)
    return user


async def require_admin(user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        logger.warning("User missing admin privileges: id=%s username=%s role=%s", getattr(user, "id", None), getattr(user, "username", None), getattr(user, "role", None))
        raise HTTPException(status_code=403, detail="Admin privileges required")
    logger.debug("Admin check passed for user id=%s", user.id)
    return user
