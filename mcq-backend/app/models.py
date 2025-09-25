from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default="student")  # 'student' or 'admin'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    quizzes_created = relationship("QuizMeta", back_populates="creator")
    results = relationship("QuizResult", back_populates="user")
    books = relationship("Book", back_populates="owner")


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(String(255), unique=True, index=True, nullable=False)  # ID used by vectordb
    title = Column(String(255), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # who ingested
    inserted_chunks = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="books")


class Chunk(Base):
    __tablename__ = "chunks"
    chunk_id = Column(String(64), primary_key=True, index=True)
    book_id = Column(String(255), index=True, nullable=False)
    chapter_name = Column(String(255), nullable=True)
    page = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    chunk_hash = Column(String(128), nullable=False, index=True)
    full_text = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("book_id", "chunk_hash", name="uq_book_chunkhash"),
    )


class QuizMeta(Base):
    __tablename__ = "quiz_meta"
    quiz_id = Column(String(100), primary_key=True, index=True)
    quiz_title = Column(String(255))
    book_id = Column(String(255))
    chapter_name = Column(String(255), nullable=True)
    raw_json = Column(Text)  # store the raw quiz JSON LLM returned
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="quizzes_created")
    results = relationship("QuizResult", back_populates="quiz")


class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(String(100), ForeignKey("quiz_meta.quiz_id"))
    score = Column(Float)
    total = Column(Integer)
    details = Column(Text)  # JSON string of details
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="results")
    quiz = relationship("QuizMeta", back_populates="results")
