from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.auth import get_current_user, require_admin
from app import schemas, models
from app.services.quiz_service import generate_quiz_and_store
import json
from app.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/quizzes", tags=["quizzes"])

@router.post("/generate", response_model=schemas.GenerateQuizResponse, summary="Generate quiz (logged-in users)")
async def generate_quiz(
    payload: schemas.GenerateQuizRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    book_id = payload.book_id
    chapter_name = payload.chapter_name
    chapters_json = payload.chapters_json
    examples = payload.examples
    difficulty = payload.difficulty
    num_questions = payload.num_questions
    use_fake_ai = payload.use_fake_ai
    llm_provider = payload.llm_provider

    logger.info("Generate quiz requested: user_id=%s book_id=%s chapter=%s num_questions=%s", current_user.id, book_id, chapter_name, num_questions)
    parsed_chapters = None
    if chapters_json:
        try:
            parsed = json.loads(chapters_json)
            if isinstance(parsed, list):
                parsed_chapters = parsed
            else:
                parsed_chapters = [s.strip() for s in str(chapters_json).split(",") if s.strip()]
        except Exception:
            parsed_chapters = [s.strip() for s in str(chapters_json).split(",") if s.strip()]

    try:
        res = await generate_quiz_and_store(
            db=db,
            created_by_user_id=current_user.id,
            book_id=book_id,
            chapter_name=chapter_name,
            chapters_json=parsed_chapters,
            examples=examples,
            difficulty=difficulty,
            num_questions=num_questions,
            use_fake_ai=use_fake_ai,
            llm_provider=llm_provider
        )
        logger.info("Quiz generated: user_id=%s quiz_id=%s", current_user.id, res.get("quiz_id"))
    except ValueError as e:
        logger.exception("Quiz generation ValueError for user_id=%s: %s", current_user.id, e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate quiz for user_id=%s: %s", current_user.id, e)
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {e}")

    return res

@router.get("/list")
async def list_quizzes(limit: int = 20, db: AsyncSession = Depends(get_db)):
    logger.debug("List quizzes (limit=%s) requested", limit)
    rows_result = await db.execute(select(models.QuizMeta).order_by(models.QuizMeta.created_at.desc()).limit(limit))
    rows = rows_result.scalars().all()
    out = []
    for q in rows:
        try:
            parsed = json.loads(q.raw_json)
        except Exception:
            parsed = {"quiz_title": q.quiz_title or "Imported Quiz", "num_questions": 0}
        out.append({
            "quiz_id": q.quiz_id,
            "quiz": {
                "quiz_title": parsed.get("quiz_title", q.quiz_title),
                "source_book": parsed.get("source_book", q.book_id),
                "scope": parsed.get("scope", f"book={q.book_id}"),
                "difficulty": parsed.get("difficulty", "medium"),
                "num_questions": parsed.get("num_questions", len(parsed.get("questions", []))),
            },
        })
    return out

@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)):
    logger.debug("Get quiz requested: quiz_id=%s", quiz_id)
    r = await db.execute(select(models.QuizMeta).where(models.QuizMeta.quiz_id == quiz_id))
    q = r.scalars().first()
    if not q:
        logger.warning("Get quiz failed - not found: %s", quiz_id)
        raise HTTPException(status_code=404, detail="Quiz not found")
    try:
        return json.loads(q.raw_json)
    except Exception:
        logger.exception("Stored quiz JSON corrupt for quiz_id=%s", quiz_id)
        raise HTTPException(status_code=500, detail="Stored quiz JSON corrupt")

@router.post("/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, submission: schemas.Submission, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    logger.info("Quiz submission: user_id=%s quiz_id=%s", current_user.id, quiz_id)
    r = await db.execute(select(models.QuizMeta).where(models.QuizMeta.quiz_id == quiz_id))
    q = r.scalars().first()
    if not q:
        logger.warning("Submit failed - quiz not found: %s", quiz_id)
        raise HTTPException(status_code=404, detail="Quiz not found")
    try:
        quiz = json.loads(q.raw_json)
    except Exception:
        logger.exception("Stored quiz JSON corrupt for quiz_id=%s", quiz_id)
        raise HTTPException(status_code=500, detail="Stored quiz JSON corrupt")

    questions = quiz.get("questions", [])
    if len(submission.answers) != len(questions):
        logger.warning("Submission answer count mismatch: user_id=%s quiz_id=%s", current_user.id, quiz_id)
        raise HTTPException(status_code=400, detail="Answer count mismatch")

    total = len(questions)
    correct_count = 0
    details = []
    for idx, ques in enumerate(questions):
        correct = set(ques.get("correct_answers", []))
        given = set(submission.answers[idx])
        is_correct = (correct == given)
        if is_correct:
            correct_count += 1
        details.append({
            "id": ques.get("id"),
            "question": ques.get("question"),
            "given": list(given),
            "correct": list(correct),
            "is_correct": is_correct,
            "explanation": ques.get("explanation", "")
        })
    score = (correct_count / total) * 100.0

    result = models.QuizResult(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        total=total,
        details=json.dumps(details)
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    logger.info("Quiz result stored: user_id=%s quiz_id=%s result_id=%s score=%s", current_user.id, quiz_id, result.id, score)

    return {"score": score, "total": total, "details": details, "result_id": result.id}

@router.get("/me/results")
async def get_my_results(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    logger.debug("Get results for user_id=%s", current_user.id)
    # join QuizMeta so we can return quiz_title and chapter_name
    stmt = (
        select(models.QuizResult, models.QuizMeta)
        .join(models.QuizMeta, models.QuizResult.quiz_id == models.QuizMeta.quiz_id, isouter=True)
        .where(models.QuizResult.user_id == current_user.id)
        .order_by(models.QuizResult.submitted_at.desc())
    )
    rows = await db.execute(stmt)
    out = []
    for qr, qm in rows.all():
        out.append({
            "id": qr.id,
            "quiz_id": qr.quiz_id,
            "quiz_title": getattr(qm, "quiz_title", None) if qm else None,
            "chapter_name": getattr(qm, "chapter_name", None) if qm else None,
            "score": qr.score,
            "total": qr.total,
            "details": json.loads(qr.details) if qr.details else [],
            "submitted_at": qr.submitted_at.isoformat() if qr.submitted_at else None
        })
    return out


@router.delete("/{quiz_id}", summary="Delete quiz (admin only)")
async def delete_quiz(quiz_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_admin)):
    logger.info("Delete quiz request by admin_id=%s quiz_id=%s", current_user.id, quiz_id)
    r = await db.execute(select(models.QuizMeta).where(models.QuizMeta.quiz_id == quiz_id))
    q = r.scalars().first()
    if not q:
        logger.warning("Delete quiz failed - not found: %s", quiz_id)
        raise HTTPException(status_code=404, detail="Quiz not found")
    await db.delete(q)
    await db.commit()
    logger.info("Quiz deleted: quiz_id=%s by admin_id=%s", quiz_id, current_user.id)
    return {"deleted": True, "quiz_id": quiz_id}


@router.get("/result/all", summary="List all quiz results (admin only)")
async def get_all_results(db: AsyncSession = Depends(get_db), current_user = Depends(require_admin)):
    logger.info("Admin listing all results: admin_id=%s", current_user.id)
    # join User and QuizMeta
    stmt = (
        select(models.QuizResult, models.User, models.QuizMeta)
        .join(models.User, models.QuizResult.user_id == models.User.id)
        .join(models.QuizMeta, models.QuizResult.quiz_id == models.QuizMeta.quiz_id, isouter=True)
        .order_by(models.QuizResult.submitted_at.desc())
    )
    rows = await db.execute(stmt)
    out = []
    for qr, user, qm in rows.all():
        out.append({
            "id": qr.id,
            "quiz_id": qr.quiz_id,
            "quiz_title": getattr(qm, "quiz_title", None) if qm else None,
            "chapter_name": getattr(qm, "chapter_name", None) if qm else None,
            "user_id": qr.user_id,
            "username": user.username if user else None,
            "score": qr.score,
            "total": qr.total,
            "details": json.loads(qr.details) if qr.details else [],
            "submitted_at": qr.submitted_at.isoformat() if qr.submitted_at else None
        })
    return out


@router.get("/result/{result_id}", summary="Get a single result together with quiz questions")
async def get_result_with_questions(result_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    # fetch the result
    stmt = select(models.QuizResult).where(models.QuizResult.id == result_id)
    r = (await db.execute(stmt)).scalars().first()
    if not r:
        logger.warning("Result not found: %s", result_id)
        raise HTTPException(status_code=404, detail="Result not found")

    # permission
    if r.user_id != current_user.id and getattr(current_user, "role", None) != "admin":
        logger.warning("Unauthorized result access attempt by user_id=%s for result_id=%s", current_user.id, result_id)
        raise HTTPException(status_code=403, detail="Not allowed to view this result")

    # get quiz meta/raw json
    qstmt = select(models.QuizMeta).where(models.QuizMeta.quiz_id == r.quiz_id)
    qmeta = (await db.execute(qstmt)).scalars().first()
    if not qmeta:
        logger.warning("Quiz meta not found for quiz_id=%s (result_id=%s)", r.quiz_id, result_id)
        raise HTTPException(status_code=404, detail="Quiz not found")

    try:
        quiz_json = json.loads(qmeta.raw_json)
    except Exception:
        logger.exception("Failed to parse stored quiz JSON for quiz_id=%s", r.quiz_id)
        quiz_json = {"questions": []}

    # parse stored details safely
    try:
        details = json.loads(r.details) if r.details else []
    except Exception:
        details = r.details or []

    # retrieve username
    user_stmt = select(models.User).where(models.User.id == r.user_id)
    user_row = (await db.execute(user_stmt)).scalars().first()
    username = user_row.username if user_row else None

    return {
        "result_id": r.id,
        "quiz_id": r.quiz_id,
        "quiz_title": getattr(qmeta, "quiz_title", None),
        "chapter_name": getattr(qmeta, "chapter_name", None),
        "user_id": r.user_id,
        "username": username,
        "score": r.score,
        "total": r.total,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "details": details,
        "questions": quiz_json.get("questions", [])
    }