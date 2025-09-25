from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any

# Auth
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: Optional[str] = "student"

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# Quiz related
class GenerateQuizResponse(BaseModel):
    quiz_id: str
    quiz: dict

class Submission(BaseModel):
    answers: List[List[int]] = ...

class QuizResultOut(BaseModel):
    id: int
    quiz_id: str
    score: float
    total: int
    details: Any
    submitted_at: str

    model_config = ConfigDict(from_attributes=True)

class GenerateQuizRequest(BaseModel):
    book_id: str
    chapter_name: Optional[str] = None
    chapters_json: Optional[str] = None
    examples: Optional[str] = ""
    difficulty: str = "medium"
    num_questions: int = 10
    use_fake_ai: bool = False
    llm_provider: str = "gemini"