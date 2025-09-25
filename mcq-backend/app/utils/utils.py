import os
from dotenv import load_dotenv
import anyio
from app.logger import get_logger

load_dotenv()
logger = get_logger()

GEMINI_AVAILABLE = False
try:
    import google.genai as genai_mod
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

def build_prompt(context: str, examples: str, difficulty: str, num_questions: int, scope: str, book_id: str):
    """
    Improved prompt for generating realistic exam-style MCQs.

    Notes for the model (enforced in the prompt below):
    - Produce exactly `num_questions` items following the JSON schema.
    - Mix question types: 'single', 'multiple', 'true_false', 'assertion_reason'.
    - Do NOT reference meta-phrases like "Based on the text", "The text explains", "as per example", etc.
    - Explanations must be standalone: explain answer reasoning in clear student-friendly language,
      without referring to the instruction context or text location.
    - For assertion_reason items, follow the 4-code format described below; for true_false, use options ["True","False"].
    - Distractors must be plausible and matched to the correct option in length/complexity.
    """

    examples_block = ""
    if examples and str(examples).strip():
        examples_block = f"""
EXAMPLES:
----EXAMPLES START----
{examples}
----EXAMPLES END----
"""
        
    pb = f"""
You are an expert exam-writer and item-writer for university-level and high-school exams. Using the supplied CONTEXT (which you may use to derive facts, concepts, formulas and examples), generate exactly {num_questions} exam-quality questions consistent with the requested difficulty ({difficulty}) and scope ({scope}). The questions must read like real practice/test questions — not like commentary about the input. Use your general knowledge + the provided context to produce accurate, self-contained items.

CRITICAL RULES (must follow exactly):
1. RETURN ONLY valid JSON matching the **exact schema** below (no extra text, no explanation outside the JSON).
2. DO NOT use any meta-references such as "based on the text", "the text explains", "as per example", "see above", or "in the passage". Each question and explanation must be fully standalone and understandable without saying "the text".
3. The explanation must be a student-facing, concise but self-contained justification of the correct answer(s) — include key facts, derivations, or brief reasoning — do not say "SOURCE MISSING:" or similar. If the context is not sufficient to be certain, write a clear reasoning sentence that states the assumption made and why the chosen option is best.
4. Produce a realistic mix of item types: single-correct, multiple-correct, true/false (as short statements), and assertion–reason items. Vary stems and cognitive level; include application, analysis, and reasoning items where appropriate.
5. Distractors must be plausible, similar in length/style to the correct option, and avoid obvious grammatical or length cues that reveal the key.
6. For true/false items, the 'options' must be ["True","False"]. Make each true/false statement unambiguous.
7. For assertion–reason items, encode the question as described in the JSON schema (see mapping below). Use the standard 4-code answer set:
   - code 1 -> "Both A and R are true. R is the correct explanation of A."
   - code 2 -> "Both A and R are true, but R is NOT the correct explanation of A."
   - code 3 -> "A is true, R is false."
   - code 4 -> "A is false, R is true."
   Represent the selected code using 0-based indices in the 'correct_answers' array (so code 1 -> index 0, code 2 -> index 1, etc).

JSON SCHEMA (strict — use exactly this structure):
{{
  "quiz_title": "<string>",                # short descriptive title
  "source_book": "{book_id}",
  "scope": "{scope}",
  "difficulty": "{difficulty}",
  "num_questions": {num_questions},
  "questions": [
    {{
      "id": <int>,                         # 0-based or 1-based index you choose, be consistent
      "type": "<single|multiple|true_false|assertion_reason>",
      "question": "<string>",              # For assertion_reason: short prefix like 'Assertion:' and 'Reason:' may be included in 'question'
      "options": ["opt1", "opt2", ...],    # For true_false: ["True","False"] ; for assertion_reason use 4 textual options explained below
      "correct_answers": [<indices 0-based>], # for multiple there may be >1 index
      "explanation": "<standalone explanation for the correct answer(s)>"
    }}
  ]
}}

HOW TO ENCODE SPECIAL ITEM TYPES (required):
- true_false:
  * type = "true_false"
  * options = ["True","False"]
  * correct_answers = [0]  # if statement is True, or [1] if False
  * explanation: short, unambiguous justification.

- assertion_reason:
  * type = "assertion_reason"
  * question: MUST contain two separate sentences: first the Assertion (A). second the Reason (R). Example: "Assertion: [A sentence]. Reason: [R sentence]."
  * options: MUST be the four textual choices exactly as strings:
      ["Both A and R are true; R is the correct explanation of A.",
       "Both A and R are true; R is NOT the correct explanation of A.",
       "A is true; R is false.",
       "A is false; R is true."]
  * correct_answers: a single-element list with the 0-based index of the chosen option (0..3).
  * explanation: explain why the chosen code is correct and briefly analyze both A and R.

ADDITIONAL STYLE / QUALITY RULES:
- Stems should be phrased as clear questions — prefer direct question format (not sentence completion) and keep them concise.
- Distractors should reflect common student mistakes or plausible misconceptions; avoid distractors that are obviously implausible.
- For multiple-correct items, include at least 2 correct choices and ensure the distractors are plausible.
- Avoid "trick" phrasing or double negatives. Prefer positive, clear phrasing except where negation is necessary and clearly signaled.
- When the context includes formulas / numbers, use them in worked reasoning in the explanation (show brief calculation when necessary).
- Use consistent notation and units in options and explanations.

CONTEXT (use for content generation — but do NOT refer to it in the output as "the text"):
----CONTEXT START----
{context}
----CONTEXT END----

{examples_block}

Return JSON only (no commentary, no extra text). Make the JSON parsable by standard JSON decoders.
"""
    return pb


def validate_quiz_json(obj: dict) -> bool:
    if not isinstance(obj, dict): return False
    required_root_fields = {"quiz_title", "source_book", "scope", "difficulty", "num_questions", "questions"}
    if not required_root_fields.issubset(set(obj.keys())): return False
    if not isinstance(obj["questions"], list): return False
    for q in obj["questions"]:
        if not isinstance(q, dict): return False
        if not {"id", "type", "question", "options", "correct_answers", "explanation"}.issubset(set(q.keys())):
            return False
        if not isinstance(q["options"], list) or len(q["options"]) < 2:
            return False
    return True

def fake_generate_quiz(num_questions: int, book_id: str, chapter_name: str, difficulty: str):
    questions = []
    for i in range(num_questions):
        questions.append({
            "id": i+1,
            "type": "single" if (i % 5 != 0) else "multiple",
            "question": f"SAMPLE: What is sample question {i+1} for {chapter_name or 'book '+book_id}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answers": [0] if (i % 5 != 0) else [0,1],
            "explanation": f"Explanation for sample Q {i+1}."
        })
    return {
        "quiz_title": f"Auto Quiz — {chapter_name or book_id}",
        "source_book": book_id,
        "scope": f"book={book_id}" + (f",chapter={chapter_name}" if chapter_name else ""),
        "difficulty": difficulty,
        "num_questions": num_questions,
        "questions": questions
    }

def _call_gemini_sync(prompt: str, model: str = "gemini-2.5-flash") -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not configured")
        raise RuntimeError("Set GEMINI_API_KEY env var to call Gemini")

    if not GEMINI_AVAILABLE:
        logger.error("google-genai package not installed.")
        raise RuntimeError("google-genai package not installed. Install it with: pip install google-genai")

    logger.info("Calling Gemini (sync wrapper) model=%s prompt_len=%d", model, len(prompt))
    try:
        client = genai_mod.Client(api_key=api_key)
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            parts = []
            for cand in getattr(resp, "candidates", []) or (resp.get("candidates") if isinstance(resp, dict) else []):
                content = getattr(cand, "content", None) or (cand.get("content") if isinstance(cand, dict) else None)
                if not content:
                    continue
                cand_parts = getattr(content, "parts", None) or (content.get("parts") if isinstance(content, dict) else None)
                if cand_parts:
                    for part in cand_parts:
                        text = getattr(part, "text", None) or (part.get("text") if isinstance(part, dict) else None)
                        if text:
                            parts.append(text)
            out = "\n".join(parts).strip()
            if out:
                logger.debug("Gemini call returned response length=%d", len(out))
                return out
        except Exception as e:
            logger.exception("Gemini SDK call failed: %s", e)
    except Exception as e:
        logger.exception("Gemini client init failed: %s", e)

    raise RuntimeError("Gemini call failed (no usable response)")

async def call_gemini(prompt: str, model: str = "gemini-2.5-flash") -> str:
    logger.debug("Async wrapper for call_gemini")
    return await anyio.to_thread.run_sync(_call_gemini_sync, prompt, model)
