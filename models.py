from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_language: Mapped[str] = mapped_column(String(64), default="English", nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_study_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    words: Mapped[List["UserWord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    grammar_results: Mapped[List["UserGrammarResult"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    grammar_progress: Mapped[List["GrammarProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    translations: Mapped[List["TranslationHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (UniqueConstraint("english", "level", name="uq_words_english_level"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    english: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    translation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    translation_ru: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    russian: Mapped[str] = mapped_column(String(255), nullable=False)
    transcription: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    level: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    example_en: Mapped[str] = mapped_column(Text, nullable=False)
    example_ru: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    user_words: Mapped[List["UserWord"]] = relationship(back_populates="word", cascade="all, delete-orphan")


class UserWord(Base):
    __tablename__ = "user_words"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_words_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    learning_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    learning_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_learning_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="words")
    word: Mapped["Word"] = relationship(back_populates="user_words")


class GrammarTask(Base):
    __tablename__ = "grammar_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(255), nullable=False)
    option_b: Mapped[str] = mapped_column(String(255), nullable=False)
    option_c: Mapped[str] = mapped_column(String(255), nullable=False)
    option_d: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    results: Mapped[List["UserGrammarResult"]] = relationship(back_populates="grammar_task", cascade="all, delete-orphan")


class UserGrammarResult(Base):
    __tablename__ = "user_grammar_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    grammar_task_id: Mapped[int] = mapped_column(ForeignKey("grammar_tasks.id"), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="grammar_results")
    grammar_task: Mapped["GrammarTask"] = relationship(back_populates="results")


class GrammarLesson(Base):
    __tablename__ = "grammar_lessons"
    __table_args__ = (UniqueConstraint("unit", name="uq_grammar_lessons_unit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    source_book: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_unit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    title_ru: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_ru: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    common_mistakes: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    questions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GrammarProgress(Base):
    __tablename__ = "grammar_progress"
    __table_args__ = (UniqueConstraint("user_id", "unit", name="uq_grammar_progress_user_unit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    unit: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="grammar_progress")


class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(64), default="auto", nullable=False)
    direction: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="translations")
