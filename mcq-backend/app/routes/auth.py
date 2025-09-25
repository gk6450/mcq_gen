from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, models
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from app.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserOut)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    logger.info("Register attempt for username=%s", user_in.username)
    q = await db.execute(select(models.User).where(models.User.username == user_in.username))
    if q.scalars().first():
        logger.warning("Register failed - username already exists: %s", user_in.username)
        raise HTTPException(status_code=400, detail="Username already registered")
    if user_in.email:
        q2 = await db.execute(select(models.User).where(models.User.email == user_in.email))
        if q2.scalars().first():
            logger.warning("Register failed - email already exists: %s", user_in.email)
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed = await hash_password(user_in.password)
    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed,
        role="student"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("User registered: id=%s username=%s", user.id, user.username)
    return user

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    logger.info("Login attempt for username=%s", form_data.username)
    q = await db.execute(select(models.User).where(models.User.username == form_data.username))
    user = q.scalars().first()
    if not user:
        logger.warning("Login failed - user not found: %s", form_data.username)
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    ok = await verify_password(form_data.password, user.hashed_password)
    if not ok:
        logger.warning("Login failed - bad password for username=%s", form_data.username)
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=int(60*24))
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    logger.info("Login successful for username=%s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut, summary="Get current user")
async def me(current_user = Depends(get_current_user)):
    """
    Return the currently authenticated user (including role).
    """
    return current_user