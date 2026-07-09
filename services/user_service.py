from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from telegram import User as TelegramUser

from config import get_admin_telegram_ids
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


def record_study_activity(user: User) -> None:
    today = date.today()
    if user.last_study_date == today:
        return

    if user.last_study_date == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1

    user.last_study_date = today


def add_user_xp(db: Session, user: User, amount: int) -> None:
    user.xp += amount
    record_study_activity(user)
    user.last_active_at = datetime.utcnow()


def is_admin_telegram_id(telegram_id: int) -> bool:
    admin_ids = get_admin_telegram_ids()
    if not admin_ids:
        return True
    return telegram_id in admin_ids


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
