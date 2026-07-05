from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import UserWord, Word


def build_learning_session_id(user_id: int, topic: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    safe_topic = (topic or "general").replace(":", "_")
    return f"{user_id}:{safe_topic}:{timestamp}"


def get_active_learning_session_for_topic(db: Session, user_id: int, topic: str) -> Optional[str]:
    statement = (
        select(UserWord.learning_session_id)
        .join(UserWord.word)
        .where(
            UserWord.user_id == user_id,
            UserWord.status == "learning",
            UserWord.is_learning_done.is_(False),
            UserWord.learning_session_id.is_not(None),
            Word.topic == topic,
        )
        .order_by(UserWord.created_at.desc(), UserWord.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def get_active_learning_session_id(db: Session, user_id: int) -> Optional[str]:
    statement = (
        select(UserWord.learning_session_id)
        .where(
            UserWord.user_id == user_id,
            UserWord.status == "learning",
            UserWord.is_learning_done.is_(False),
            UserWord.learning_session_id.is_not(None),
        )
        .order_by(UserWord.created_at.desc(), UserWord.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def count_learning_words(
    db: Session,
    user_id: int,
    learning_session_id: Optional[str] = None,
    only_not_done: bool = False,
) -> int:
    statement = (
        select(func.count())
        .select_from(UserWord)
        .where(UserWord.user_id == user_id, UserWord.status == "learning")
    )
    if learning_session_id:
        statement = statement.where(UserWord.learning_session_id == learning_session_id)
    if only_not_done:
        statement = statement.where(UserWord.is_learning_done.is_(False))
    return db.scalar(statement) or 0


def count_learning_done(db: Session, user_id: int, learning_session_id: str) -> int:
    statement = (
        select(func.count())
        .select_from(UserWord)
        .where(
            UserWord.user_id == user_id,
            UserWord.learning_session_id == learning_session_id,
            UserWord.is_learning_done.is_(True),
        )
    )
    return db.scalar(statement) or 0


def get_next_learning_word(
    db: Session,
    user_id: int,
    learning_session_id: Optional[str] = None,
    exclude_user_word_id: Optional[int] = None,
) -> Optional[UserWord]:
    statement = (
        select(UserWord)
        .options(selectinload(UserWord.word))
        .where(
            UserWord.user_id == user_id,
            UserWord.status == "learning",
            UserWord.is_learning_done.is_(False),
        )
    )
    if learning_session_id:
        statement = statement.where(UserWord.learning_session_id == learning_session_id)
    if exclude_user_word_id is not None:
        statement = statement.where(UserWord.id != exclude_user_word_id)

    return db.scalar(statement.order_by(UserWord.last_reviewed_at.asc(), UserWord.id.asc()).limit(1))


def complete_learning_session(db: Session, user_id: int, learning_session_id: str, now: datetime) -> int:
    words = list(
        db.scalars(
            select(UserWord).where(
                UserWord.user_id == user_id,
                UserWord.learning_session_id == learning_session_id,
                UserWord.status == "learning",
            )
        )
    )
    for user_word in words:
        user_word.status = "review"
        user_word.is_learning_done = True
        user_word.review_streak = 0
        user_word.interval_days = 0
        user_word.next_review_at = now + timedelta(minutes=5)
    return len(words)


def get_learning_stats(
    db: Session,
    user_id: int,
    learning_session_id: Optional[str] = None,
) -> Dict[str, object]:
    active_session_id = learning_session_id or get_active_learning_session_id(db, user_id)
    learning_total = count_learning_words(db, user_id)
    learning_not_done = count_learning_words(db, user_id, only_not_done=True)
    learning_done = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .where(
                UserWord.user_id == user_id,
                UserWord.status == "learning",
                UserWord.is_learning_done.is_(True),
            )
        )
        or 0
    )

    current_session_done = 0
    current_session_not_done = 0
    if active_session_id:
        current_session_done = count_learning_done(db, user_id, active_session_id)
        current_session_not_done = count_learning_words(
            db,
            user_id,
            learning_session_id=active_session_id,
            only_not_done=True,
        )

    return {
        "active_session_id": active_session_id or "нет",
        "learning_total": int(learning_total),
        "learning_not_done": int(learning_not_done),
        "learning_done": int(learning_done),
        "current_session_done": int(current_session_done),
        "current_session_not_done": int(current_session_not_done),
    }


def get_debug_learning_words(
    db: Session,
    user_id: int,
    learning_session_id: Optional[str] = None,
    limit: int = 20,
) -> List[UserWord]:
    statement = (
        select(UserWord)
        .options(selectinload(UserWord.word))
        .where(UserWord.user_id == user_id)
    )
    if learning_session_id:
        statement = statement.where(UserWord.learning_session_id == learning_session_id)
    else:
        statement = statement.where(UserWord.status == "learning")

    statement = statement.order_by(UserWord.is_learning_done.asc(), UserWord.id.asc()).limit(limit)
    return list(db.scalars(statement))
