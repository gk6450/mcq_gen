from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
import uuid
from app.logger import get_logger
from app.vectordb_pinecone import upsert_book_to_pinecone, list_chapters_for_book

logger = get_logger()


async def ingest_book_and_record(
    db: AsyncSession,
    pdf_bytes: bytes,
    ingested_by_user_id: int,
    book_id: Optional[str] = None,
    chapters: Optional[List[Dict[str, Any]]] = None,
):
    """
    Ingest the PDF into vectordb and record/update book metadata in Postgres.
    `chapters` must be either None or a list of dicts like:
      [{"name": "Chapter 3", "start_page": 10, "end_page": 20}, ...]
    """
    book_id_to_use = book_id or str(uuid.uuid4())
    logger.info("Book ingest started: user_id=%s book_id=%s chapters=%s", ingested_by_user_id, book_id_to_use, chapters)

    # async upsert to pinecone (and DB chunk storage) — returns dict
    res = await upsert_book_to_pinecone(book_id=book_id_to_use, pdf_bytes=pdf_bytes, chapters=chapters)
    book_id_final = res.get("book_id") or book_id_to_use
    inserted = res.get("inserted", 0)
    skipped = res.get("skipped", 0)

    # record metadata in Postgres (async)
    q = await db.execute(select(models.Book).where(models.Book.book_id == book_id_final))
    book = q.scalars().first()
    if book:
        logger.debug("Updating existing book metadata book_id=%s", book_id_final)
        book.inserted_chunks = inserted
    else:
        book = models.Book(book_id=book_id_final, title=None, owner_id=ingested_by_user_id, inserted_chunks=inserted)
        db.add(book)
    await db.commit()
    await db.refresh(book)
    logger.info("Book ingest recorded: book_id=%s inserted=%s skipped=%s", book_id_final, inserted, skipped)
    return {"book_id": book_id_final, "inserted": inserted, "skipped": skipped}


async def get_chapters(book_id: str) -> List[str]:
    logger.debug("Getting chapters for book_id=%s", book_id)
    return await list_chapters_for_book(book_id)
