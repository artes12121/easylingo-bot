from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from models import UserWord
from services.learning_service import build_learning_session_id

MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5


def _due_review_status_filter():
    return or_(
        UserWord.status == "review",
        and_(UserWord.status == "learning", UserWord.is_learning_done.is_(False)),
        UserWord.status == "known",
    )


def _schedule_short_review(user_word: UserWord, now: datetime) -> None:
    user_word.interval_days = 0
    user_word.next_review_at = now + timedelta(minutes=5)


def _apply_sm2_success(user_word: UserWord, now: datetime) -> None:
    if user_word.interval_days <= 0:
        user_word.interval_days = 1
    elif user_word.interval_days == 1:
        user_word.interval_days = 3
    else:
        user_word.interval_days = max(1, int(round(user_word.interval_days * user_word.ease_factor)))
    user_word.ease_factor = min(2.5, user_word.ease_factor + 0.1)
    user_word.next_review_at = now + timedelta(days=user_word.interval_days)


def count_due_reviews(db: Session, user_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(UserWord)
        .where(
            UserWord.user_id == user_id,
            _due_review_status_filter(),
            UserWord.next_review_at <= datetime.utcnow(),
        )
    )
    return db.scalar(statement) or 0


def get_user_word(db: Session, user_id: int, user_word_id: int) -> Optional[UserWord]:
    statement = (
        select(UserWord)
        .options(selectinload(UserWord.word))
        .where(UserWord.id == user_word_id, UserWord.user_id == user_id)
    )
    return db.scalar(statement)


def get_next_due_review(db: Session, user_id: int) -> Optional[UserWord]:
    statement = (
        select(UserWord)
        .options(selectinload(UserWord.word))
        .where(
            UserWord.user_id == user_id,
            _due_review_status_filter(),
            UserWord.next_review_at <= datetime.utcnow(),
        )
        .order_by(UserWord.next_review_at.asc(), UserWord.id.asc())
        .limit(1)
    )
    return db.scalar(statement)


def create_user_word(
    db: Session,
    user_id: int,
    word_id: int,
    status: str,
    interval_days: int,
    correct_count: int = 0,
    wrong_count: int = 0,
    learning_stage: int = 0,
    review_streak: int = 0,
    learning_session_id: Optional[str] = None,
    is_learning_done: bool = False,
    next_review_at: Optional[datetime] = None,
    last_reviewed_at: Optional[datetime] = None,
) -> Tuple[UserWord, bool]:
    existing = db.scalar(select(UserWord).where(UserWord.user_id == user_id, UserWord.word_id == word_id))
    if existing:
        return existing, False

    now = datetime.utcnow()
    user_word = UserWord(
        user_id=user_id,
        word_id=word_id,
        status=status,
        correct_count=correct_count,
        wrong_count=wrong_count,
        learning_stage=learning_stage,
        review_streak=review_streak,
        learning_session_id=learning_session_id,
        is_learning_done=is_learning_done,
        interval_days=interval_days,
        next_review_at=next_review_at or now + timedelta(days=interval_days),
        last_reviewed_at=last_reviewed_at,
    )
    db.add(user_word)
    db.flush()
    return user_word, True


def update_review_result(user_word: UserWord, is_correct: bool) -> None:
    now = datetime.utcnow()
    user_word.last_reviewed_at = now

    if is_correct:
        user_word.correct_count += 1

        if user_word.status == "learning":
            user_word.learning_stage += 1
            _schedule_short_review(user_word, now)
            if user_word.learning_stage >= 3:
                user_word.status = "review"
                user_word.is_learning_done = True
                user_word.review_streak = 0
            return

        if user_word.status == "known":
            _apply_sm2_success(user_word, now)
            return

        user_word.review_streak += 1
        if user_word.review_streak >= 3:
            user_word.status = "known"
            user_word.interval_days = 7
            user_word.next_review_at = now + timedelta(days=7)
            user_word.ease_factor = max(user_word.ease_factor, DEFAULT_EASE_FACTOR)
            return

        user_word.status = "review"
        _schedule_short_review(user_word, now)
        return

    user_word.wrong_count += 1
    user_word.review_streak = 0
    user_word.learning_stage = 0

    if user_word.status == "known":
        user_word.status = "review"
        user_word.ease_factor = max(MIN_EASE_FACTOR, user_word.ease_factor - 0.2)
        _schedule_short_review(user_word, now)
        return

    user_word.status = "learning"
    user_word.is_learning_done = False
    user_word.learning_session_id = build_learning_session_id(
        user_word.user_id,
        user_word.word.topic if user_word.word else "review",
    )
    _schedule_short_review(user_word, now)


def get_user_word_stats(db: Session, user_id: int) -> Dict[str, int]:
    learned_words = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id)
        )
        or 0
    )
    due_reviews = count_due_reviews(db, user_id)
    known_words = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id, UserWord.status == "known")
        )
        or 0
    )
    learning_words = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id, UserWord.status == "learning")
        )
        or 0
    )
    review_total = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id, UserWord.status == "review")
        )
        or 0
    )
    review_streak_1 = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id, UserWord.status == "review", UserWord.review_streak == 1)
        )
        or 0
    )
    review_streak_2 = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(UserWord.user_id == user_id, UserWord.status == "review", UserWord.review_streak == 2)
        )
        or 0
    )
    correct_answers = (
        db.scalar(select(func.coalesce(func.sum(UserWord.correct_count), 0)).where(UserWord.user_id == user_id))
        or 0
    )
    wrong_answers = (
        db.scalar(select(func.coalesce(func.sum(UserWord.wrong_count), 0)).where(UserWord.user_id == user_id))
        or 0
    )
    return {
        "learned_words": int(learned_words),
        "known_words": int(known_words),
        "learning_words": int(learning_words),
        "review_total": int(review_total),
        "due_reviews": int(due_reviews),
        "review_streak_1": int(review_streak_1),
        "review_streak_2": int(review_streak_2),
        "correct_answers": int(correct_answers),
        "wrong_answers": int(wrong_answers),
    }
