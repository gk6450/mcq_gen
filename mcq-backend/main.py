from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from app.database import engine, Base
from app.routes import auth as auth_router, books as books_router, quizzes as quizzes_router
from app.logger import configure_logging, get_logger

# configure logging early
configure_logging()
logger = get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application lifespan - creating DB tables (if needed)")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("DB tables are ready")
    except Exception as e:
        logger.exception("Failed to create DB tables during startup: %s", e)
        raise
    yield
    logger.info("Shutting down application lifespan")

app = FastAPI(title="MCQ_Gen API", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router.router)
app.include_router(books_router.router)
app.include_router(quizzes_router.router)
