import uuid
import json
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from app.vectordb_pinecone import retrieve_relevant_chunks
from app.utils.utils import build_prompt, validate_quiz_json, fake_generate_quiz, call_gemini
import anyio
import os
from dotenv import load_dotenv
from app.logger import get_logger

load_dotenv()
logger = get_logger()
CONTEXT_CHAR_LIMIT = int(os.getenv("CONTEXT_CHAR_LIMIT", "4000"))

def _assemble_context(hits: list, char_limit: int = CONTEXT_CHAR_LIMIT) -> str:
    context_pieces = []
    total_chars = 0
    for h in hits:
        txt = h.get("full_text", "") or ""
        if total_chars + len(txt) > char_limit:
            remaining = char_limit - total_chars
            if remaining <= 0:
                break
            context_pieces.append(txt[:remaining])
            total_chars += remaining
            break
        context_pieces.append(txt)
        total_chars += len(txt)
    return "\n\n".join(context_pieces) or " "

async def generate_quiz_and_store(
    db: AsyncSession,
    created_by_user_id: int,
    book_id: str,
    chapter_name: Optional[str] = None,
    chapters_json: Optional[Any] = None,   # accept list[dict] or JSON string
    examples: Optional[str] = "",
    difficulty: str = "medium",
    num_questions: int = 10,
    use_fake_ai: bool = False,
    llm_provider: str = "gemini"
):
    logger.info(
        "Starting quiz generation: user_id=%s book_id=%s chapter=%s num_q=%s",
        created_by_user_id, book_id, chapter_name, num_questions
    )

    # === Normalize chapter inputs into a list of chapter NAMES (strings) ===
    requested_chapters: Optional[List[str]] = None

    # If chapters_json provided, it's expected to be a list of dicts {name,start_page,end_page}
    if chapters_json:
        parsed = chapters_json
        # Accept stringified JSON or actual list
        if isinstance(chapters_json, str):
            try:
                parsed = json.loads(chapters_json)
            except Exception:
                logger.exception("Failed to parse chapters_json string; expected JSON list of {name,start_page,end_page}")
                parsed = None

        if isinstance(parsed, list):
            names: List[str] = []
            for item in parsed:
                if isinstance(item, dict):
                    name = item.get("name")
                    if name and isinstance(name, str) and name.strip():
                        names.append(name.strip())
                    else:
                        # fallback: try to find first string-like val
                        for v in item.values():
                            if isinstance(v, str) and v.strip():
                                names.append(v.strip())
                                break
                elif isinstance(item, str):
                    # allow entries that are plain strings (also allow comma-separated string entries)
                    parts = [p.strip() for p in item.split(",") if p.strip()]
                    names.extend(parts)
                else:
                    # coerce and add if meaningful
                    try:
                        s = str(item).strip()
                        if s:
                            names.append(s)
                    except Exception:
                        continue
            requested_chapters = names if names else None
        else:
            logger.warning("chapters_json provided but not a list; ignoring chapters_json")
            requested_chapters = None

    # Else if single chapter_name provided (string possibly comma-separated), normalize to list
    elif chapter_name:
        if isinstance(chapter_name, str):
            parts = [p.strip() for p in chapter_name.split(",") if p.strip()]
            requested_chapters = parts if parts else None
        elif isinstance(chapter_name, list):
            requested_chapters = [str(x).strip() for x in chapter_name if str(x).strip()]
        else:
            requested_chapters = [str(chapter_name)]

    # Build guiding scope text for LLM prompt (use comma-separated names)
    if requested_chapters:
        chapters_csv = ", ".join(requested_chapters)
        guiding_scope = f"chapters {chapters_csv}"
    elif chapter_name:
        guiding_scope = f"chapter {chapter_name}"
    else:
        guiding_scope = "the whole book"

    guiding_query = f"""
    Important content from {guiding_scope}
    including:
    - definitions
    - key formulas
    - important concepts
    - examples or explanations students should be quizzed on
    """

    # Retrieve relevant chunks from vectordb (pass list of names or None)
    hits = await retrieve_relevant_chunks(
        scope_book_id=book_id,
        scope_chapter=requested_chapters,
        query=guiding_query,
        top_k=24
    )
    logger.debug("retrieve_relevant_chunks returned %d hits for book_id=%s", len(hits), book_id)
    context = _assemble_context(hits)

    # Build scope descriptor for prompt & metadata storing
    scope = f"book={book_id}"
    if requested_chapters:
        # store comma-separated list for human-readable fields and JSON list for scope
        scope = f"book={book_id},chapters={json.dumps(requested_chapters)}"
    elif chapter_name:
        scope = f"book={book_id},chapter={chapter_name}"

    prompt = build_prompt(
        context=context,
        examples=examples,
        difficulty=difficulty,
        num_questions=num_questions,
        scope=scope,
        book_id=book_id,
    )
    logger.debug("Prompt built (len=%s) for quiz generation", len(prompt))

    # Generate quiz via fake AI or real LLM
    if use_fake_ai:
        ai_json = fake_generate_quiz(
            num_questions,
            book_id,
            (requested_chapters[0] if requested_chapters else (chapter_name or "")),
            difficulty
        )
        logger.debug("Using fake AI generator")
    else:
        logger.info("Calling LLM provider (%s) for quiz generation", llm_provider)
        raw_text = await call_gemini(prompt)
        logger.debug("LLM returned text (truncated): %s", raw_text[:400].replace("\n", " "))
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            logger.error("LLM did not return JSON-wrapped output")
            raise ValueError("LLM did not return JSON-wrapped output")
        json_text = raw_text[start:end+1]
        try:
            ai_json = json.loads(json_text)
        except Exception as e:
            logger.exception("Failed to parse LLM JSON: %s", e)
            raise ValueError(f"Failed to parse LLM JSON: {e}")

    if not validate_quiz_json(ai_json):
        logger.error("AI returned invalid quiz JSON")
        raise ValueError("AI returned invalid quiz JSON")

    # Persist quiz metadata / raw JSON
    quiz_id = str(uuid.uuid4())
    quiz_title = ai_json.get("quiz_title", f"AutoQuiz-{quiz_id}")
    chapter_name_to_store = ",".join(requested_chapters) if requested_chapters else (chapter_name or "")
    qm = models.QuizMeta(
        quiz_id=quiz_id,
        quiz_title=quiz_title,
        book_id=book_id,
        chapter_name=chapter_name_to_store,
        raw_json=json.dumps(ai_json),
        created_by=created_by_user_id
    )
    db.add(qm)
    await db.commit()
    await db.refresh(qm)
    logger.info(
        "Quiz saved: quiz_id=%s created_by=%s num_questions=%s",
        quiz_id, created_by_user_id, ai_json.get("num_questions", len(ai_json.get("questions", [])))
    )
    return {"quiz_id": quiz_id, "quiz": ai_json}

