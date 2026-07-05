from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from telegram import User as TelegramUser

from models import GrammarProgress, TranslationHistory, User, UserGrammarResult, UserWord


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    return db.scalar(select(User).where(User.telegram_id == telegram_id))


def get_or_create_user(db: Session, telegram_user: TelegramUser) -> User:
    user = get_user_by_telegram_id(db, telegram_user.id)
    if user:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_active_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    user = User(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_user_level(db: Session, telegram_id: int, level: str) -> Optional[User]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None

    user.level = level
    user.last_active_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def add_user_xp(db: Session, user: User, amount: int) -> None:
    user.xp += amount
    user.last_active_at = datetime.utcnow()


def reset_user_progress(db: Session, user: User) -> None:
    db.execute(delete(UserWord).where(UserWord.user_id == user.id))
    db.execute(delete(UserGrammarResult).where(UserGrammarResult.user_id == user.id))
    db.execute(delete(GrammarProgress).where(GrammarProgress.user_id == user.id))
    db.execute(delete(TranslationHistory).where(TranslationHistory.user_id == user.id))
    user.xp = 0
    user.streak = 0
    user.last_study_date = None
    user.last_active_at = datetime.utcnow()


def touch_user(db: Session, telegram_id: int) -> None:
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        user.last_active_at = datetime.utcnow()
        db.commit()
