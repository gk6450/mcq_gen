from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from app.database import get_db
from app.auth import get_current_user, require_admin
from app import models
from app.services import book_service
import json
from app.logger import get_logger
from app.vectordb_pinecone import extract_text_from_pdf_bytes

logger = get_logger()
router = APIRouter(prefix="/books", tags=["books"])


@router.post("/ingest", summary="Ingest a PDF into vector DB (protected - any logged-in user)")
async def ingest_book_endpoint(
    pdf_file: UploadFile = File(...),
    book_id: Optional[str] = Form(None),
    chapters_json: Optional[str] = Form(None),
    chapter_name: Optional[str] = Form(None),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a PDF file. Priority:
      1) chapters_json (stringified JSON of chapters) -> used as-is (validated)
      2) chapter_name (+ optional start_page, end_page) -> single-chapter upload
      3) None -> treat as full book (chapter_name 'full')
    Ensures chapters passed to vectordb are a list of dicts with start/end pages so prepare_chunks_from_pdf_sync
    maps pages correctly. If no chapter info provided, chapters stays None and chunks will be labelled 'full'.
    """
    logger.info("Ingest request: user_id=%s filename=%s book_id=%s", getattr(current_user, "id", None), pdf_file.filename, book_id)
    if not pdf_file.filename.lower().endswith(".pdf"):
        logger.warning("Ingest failed: non-pdf upload by user_id=%s filename=%s", getattr(current_user, "id", None), pdf_file.filename)
        raise HTTPException(status_code=400, detail="Only PDF supported")

    content = await pdf_file.read()

    chapters: Optional[List[Dict[str, Any]]] = None

    # 1) chapters_json (highest priority)
    if chapters_json:
        try:
            parsed = json.loads(chapters_json)
        except json.JSONDecodeError:
            logger.exception("Invalid chapters_json provided by user_id=%s", getattr(current_user, "id", None))
            raise HTTPException(status_code=400, detail="Invalid chapters_json. Must be JSON list of {name,start_page,end_page}")
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="chapters_json must be a JSON list")
        cleaned: List[Dict[str, Any]] = []
        for ch in parsed:
            if not isinstance(ch, dict) or "name" not in ch or "start_page" not in ch or "end_page" not in ch:
                raise HTTPException(status_code=400, detail="Each chapter must include 'name','start_page','end_page'")
            try:
                cleaned.append({
                    "name": str(ch["name"]),
                    "start_page": int(ch["start_page"]),
                    "end_page": int(ch["end_page"]),
                })
            except Exception:
                raise HTTPException(status_code=400, detail="start_page and end_page must be integers")
        chapters = cleaned

    # 2) single chapter_name path
    elif chapter_name:
        # compute total pages from PDF to determine defaults/clamping
        try:
            pages = await extract_text_from_pdf_bytes(content)
            total_pages = len(pages)
            logger.debug("PDF pages extracted: %d", total_pages)
        except Exception:
            total_pages = None

        # normalize start/end (if provided via form they may already be ints)
        try:
            s = int(start_page) if start_page is not None else 1
        except Exception:
            s = 1
        try:
            e = int(end_page) if end_page is not None else (total_pages or s)
        except Exception:
            e = total_pages or s

        # clamp by total pages if known
        if total_pages:
            if s < 1:
                s = 1
            if e > total_pages:
                e = total_pages

        if e < s:
            raise HTTPException(status_code=400, detail="end_page must be >= start_page")

        chapters = [{"name": str(chapter_name), "start_page": s, "end_page": e}]

    # else chapters stays None -> prepare_chunks marks chapter_name as "full"

    logger.info("Ingest prepared: user_id=%s book_id=%s chapters=%s", getattr(current_user, "id", None), book_id, chapters)

    try:
        res = await book_service.ingest_book_and_record(
            db=db,
            pdf_bytes=content,
            ingested_by_user_id=current_user.id,
            book_id=book_id or None,
            chapters=chapters,
        )
        logger.info("Ingest completed: user_id=%s book_id=%s inserted=%s skipped=%s",
                    current_user.id, res.get("book_id"), res.get("inserted", 0), res.get("skipped", 0))
    except Exception as e:
        logger.exception("Failed to ingest for user_id=%s: %s", current_user.id, e)
        raise HTTPException(status_code=500, detail=f"Failed to ingest: {e}")

    return {"book_id": res.get("book_id"), "inserted_chunks": res.get("inserted", 0), "skipped_chunks": res.get("skipped", 0)}


@router.get("/{book_id}/chapters", summary="List chapters for a book (public)")
async def get_book_chapters(book_id: str):
    logger.debug("List chapters request for book_id=%s", book_id)
    ch = await book_service.get_chapters(book_id)
    return {"book_id": book_id, "chapters": ch}


@router.put("/{book_id}", summary="Update book metadata (admin only)")
async def update_book(book_id: str, data: dict = Body(...), db: AsyncSession = Depends(get_db), current_user = Depends(require_admin)):
    logger.info("Update book request: admin_id=%s book_id=%s data_keys=%s", current_user.id, book_id, list(data.keys()))
    q = await db.execute(select(models.Book).where(models.Book.book_id == book_id))
    book = q.scalars().first()
    if not book:
        logger.warning("Update failed - book not found: %s", book_id)
        raise HTTPException(status_code=404, detail="Book not found")
    if "title" in data:
        book.title = data.get("title")
    if "is_active" in data:
        book.is_active = bool(data.get("is_active"))
    if "inserted_chunks" in data:
        try:
            book.inserted_chunks = int(data.get("inserted_chunks"))
        except Exception:
            pass
    await db.commit()
    await db.refresh(book)
    logger.info("Book updated: admin_id=%s book_id=%s", current_user.id, book_id)
    return {"book_id": book.book_id, "title": book.title, "is_active": book.is_active, "inserted_chunks": book.inserted_chunks}


@router.delete("/{book_id}", summary="Delete book metadata and optionally vectordb entries (admin only)")
async def delete_book(book_id: str, remove_vector: bool = False, db: AsyncSession = Depends(get_db), current_user = Depends(require_admin)):
    logger.info("Delete book request: admin_id=%s book_id=%s remove_vector=%s", current_user.id, book_id, remove_vector)
    q = await db.execute(select(models.Book).where(models.Book.book_id == book_id))
    book = q.scalars().first()
    if not book:
        logger.warning("Delete failed - book not found: %s", book_id)
        raise HTTPException(status_code=404, detail="Book not found")
    if remove_vector:
        try:
            from app.vectordb_pinecone import delete_book_from_pinecone
            await delete_book_from_pinecone(book_id)
            logger.info("Vectors removed for book_id=%s", book_id)
        except Exception:
            logger.exception("vectordb deletion failed for book_id=%s", book_id)
    await db.delete(book)
    await db.commit()
    logger.info("Book metadata deleted: book_id=%s", book_id)
    return {"deleted": True, "book_id": book_id}


@router.get("/list", summary="List uploaded books (public)")
async def list_books(db: AsyncSession = Depends(get_db)):
    """
    Return a list of uploaded books with basic metadata.
    """
    logger.debug("List books requested")
    rows = await db.execute(select(models.Book).order_by(models.Book.created_at.desc()).limit(200))
    books = rows.scalars().all()
    out = []
    for b in books:
        out.append({
            "book_id": b.book_id,
            "title": b.title,
            "owner_id": b.owner_id,
            "inserted_chunks": b.inserted_chunks,
            "is_active": b.is_active,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    return out
