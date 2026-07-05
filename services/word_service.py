from typing import Dict, List, Optional

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from models import UserWord, Word


def count_words(db: Session, level: Optional[str] = None) -> int:
    statement = select(func.count()).select_from(Word)
    if level:
        statement = statement.where(Word.level == level)
    return db.scalar(statement) or 0


def get_words_by_level(db: Session, level: str, limit: int = 10) -> List[Word]:
    return list(db.scalars(select(Word).where(Word.level == level).limit(limit)))


def get_topics_by_level(db: Session, level: str) -> List[str]:
    statement = (
        select(Word.topic)
        .where(Word.level == level)
        .where(Word.topic.is_not(None))
        .where(Word.topic != "")
        .distinct()
        .order_by(Word.topic)
    )
    return [topic for topic in db.scalars(statement) if topic]


def get_topic_stats(db: Session, user_id: int, level: str, topic: str) -> Dict[str, int]:
    total_words = (
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(Word.level == level, Word.topic == topic)
        )
        or 0
    )
    user_words_in_topic = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .join(Word)
            .where(UserWord.user_id == user_id, Word.level == level, Word.topic == topic)
        )
        or 0
    )
    known_count = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .join(Word)
            .where(
                UserWord.user_id == user_id,
                UserWord.status == "known",
                Word.level == level,
                Word.topic == topic,
            )
        )
        or 0
    )
    learning_count = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .join(Word)
            .where(
                UserWord.user_id == user_id,
                UserWord.status == "learning",
                Word.level == level,
                Word.topic == topic,
            )
        )
        or 0
    )
    review_count = (
        db.scalar(
            select(func.count())
            .select_from(UserWord)
            .join(Word)
            .where(
                UserWord.user_id == user_id,
                UserWord.status == "review",
                Word.level == level,
                Word.topic == topic,
            )
        )
        or 0
    )
    return {
        "total_words": int(total_words),
        "user_words_in_topic": int(user_words_in_topic),
        "known_count": int(known_count),
        "learning_count": int(learning_count),
        "review_count": int(review_count),
    }


def format_topic_progress_label(topic: str, stats: Dict[str, int]) -> str:
    total_words = stats["total_words"]
    user_words_in_topic = stats["user_words_in_topic"]
    if user_words_in_topic <= 0:
        icon = "⬜"
    elif user_words_in_topic < total_words:
        icon = "🔄"
    else:
        icon = "✅"
    visible_count = min(user_words_in_topic, total_words)
    return f"{icon} {topic} — {visible_count}/{total_words}"


def get_topic_progress_labels(db: Session, user_id: int, level: str, topics: List[str]) -> List[str]:
    return [format_topic_progress_label(topic, get_topic_stats(db, user_id, level, topic)) for topic in topics]


def get_word_by_id(db: Session, word_id: int) -> Optional[Word]:
    return db.get(Word, word_id)


def get_random_word_for_topic(
    db: Session,
    level: str,
    topic: str,
    exclude_word_ids: Optional[List[int]] = None,
) -> Optional[Word]:
    statement = select(Word).where(Word.level == level, Word.topic == topic)
    if exclude_word_ids:
        statement = statement.where(~Word.id.in_(exclude_word_ids))

    return db.scalar(statement.order_by(func.random()).limit(1))


def get_random_new_word_for_user(
    db: Session,
    user_id: int,
    level: str,
    exclude_word_id: Optional[int] = None,
) -> Optional[Word]:
    already_added = (
        exists()
        .where(UserWord.user_id == user_id)
        .where(UserWord.word_id == Word.id)
    )
    statement = select(Word).where(Word.level == level).where(~already_added)

    if exclude_word_id is not None:
        statement = statement.where(Word.id != exclude_word_id)

    return db.scalar(statement.order_by(func.random()).limit(1))


def get_random_new_word_for_user_by_topic(
    db: Session,
    user_id: int,
    level: str,
    topic: str,
    exclude_word_id: Optional[int] = None,
) -> Optional[Word]:
    already_added = (
        exists()
        .where(UserWord.user_id == user_id)
        .where(UserWord.word_id == Word.id)
    )
    statement = (
        select(Word)
        .where(Word.level == level)
        .where(Word.topic == topic)
        .where(~already_added)
    )

    if exclude_word_id is not None:
        statement = statement.where(Word.id != exclude_word_id)

    return db.scalar(statement.order_by(func.random()).limit(1))
