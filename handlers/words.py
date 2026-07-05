from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import (
    back_to_menu_keyboard,
    learn_topics_keyboard,
    learn_word_keyboard,
    level_keyboard,
    repeat_topic_completed_keyboard,
    topic_completed_keyboard,
)
from models import UserWord, Word
from services.learning_service import (
    build_learning_session_id,
    get_active_learning_session_for_topic,
)
from services.user_service import add_user_xp, get_or_create_user
from services.word_format_service import format_word_card as build_word_card
from services.word_service import (
    count_words,
    get_random_new_word_for_user_by_topic,
    get_random_word_for_topic,
    get_topic_progress_labels,
    get_topic_stats,
    get_topics_by_level,
    get_word_by_id,
)


async def words_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await show_word_topics(update, context)


def format_word_card(word: Word) -> str:
    return (
        "📚 Новое слово\n\n"
        f"{build_word_card(word)}\n\n"
        "Выбери действие:\n"
        "✅ Знаю — если слово уже знакомо\n"
        "❌ Не знаю — добавить в заучивание\n"
        "➡️ Следующее — пропустить"
    )


def format_repeat_word_card(word: Word) -> str:
    topic = word.topic or "general"
    return (
        f"🔁 Повтор темы: {topic}\n\n"
        f"{build_word_card(word)}\n\n"
        "Выбери действие:\n"
        "✅ Знаю — оставить как знакомое\n"
        "❌ Не знаю — вернуть в заучивание\n"
        "➡️ Следующее — пропустить"
    )

async def show_word_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        if not user.level:
            text = "Сначала выбери уровень английского:"
            reply_markup = level_keyboard()
        elif count_words(db, user.level) == 0:
            text = "В базе пока нет слов для твоего уровня. Запусти python seed_data.py."
            reply_markup = back_to_menu_keyboard()
        else:
            topics = get_topics_by_level(db, user.level)
            if not topics:
                text = "Для твоего уровня пока нет тем. Запусти python seed_data.py."
                reply_markup = back_to_menu_keyboard()
            else:
                context.user_data["word_topics"] = topics
                context.user_data.pop("learn_topic", None)
                context.user_data.pop("repeat_topic_mode", None)
                context.user_data.pop("repeat_seen_word_ids", None)
                topic_labels = get_topic_progress_labels(db, user.id, user.level, topics)
                text = "📚 Учить слова\n\nВыбери тему:"
                reply_markup = learn_topics_keyboard(topics, labels=topic_labels)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


def get_saved_learn_topic(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    topic = context.user_data.get("learn_topic")
    return topic if isinstance(topic, str) and topic else None


def get_saved_learning_session(context: ContextTypes.DEFAULT_TYPE, topic: Optional[str]) -> Optional[str]:
    session_id = context.user_data.get("learning_session_id")
    session_topic = context.user_data.get("learning_session_topic")
    if isinstance(session_id, str) and session_id and session_topic == topic:
        return session_id
    return None


def is_repeat_topic_mode(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return context.user_data.get("repeat_topic_mode") is True


def get_repeat_seen_word_ids(context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    seen_word_ids = context.user_data.get("repeat_seen_word_ids")
    if not isinstance(seen_word_ids, list):
        seen_word_ids = []
        context.user_data["repeat_seen_word_ids"] = seen_word_ids
    return [int(word_id) for word_id in seen_word_ids if isinstance(word_id, int)]


def add_repeat_seen_word_id(context: ContextTypes.DEFAULT_TYPE, word_id: int) -> None:
    seen_word_ids = context.user_data.get("repeat_seen_word_ids")
    if not isinstance(seen_word_ids, list):
        seen_word_ids = []
    if word_id not in seen_word_ids:
        seen_word_ids.append(word_id)
    context.user_data["repeat_seen_word_ids"] = seen_word_ids


async def show_topic_completed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: str,
    prefix_text: Optional[str] = None,
) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        stats = get_topic_stats(db, user.id, user.level or "", topic)
        text = (
            f"✅ Тема пройдена: {topic}\n\n"
            f"Всего слов: {stats['total_words']}\n"
            f"Знакомые: {stats['known_count']}\n"
            f"На заучивании: {stats['learning_count']}\n"
            f"В повторении: {stats['review_count']}\n\n"
            "Ты можешь пройти тему заново или перейти к повторению."
        )
        reply_markup = topic_completed_keyboard()

    if prefix_text:
        text = f"{prefix_text}\n\n{text}"

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def show_repeat_topic_completed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: str,
    prefix_text: Optional[str] = None,
) -> None:
    query = update.callback_query
    message = update.effective_message
    text = (
        f"🔁 Повтор темы завершён: {topic}\n\n"
        "Ты прошёл все слова этой темы ещё раз."
    )
    if prefix_text:
        text = f"{prefix_text}\n\n{text}"
    reply_markup = repeat_topic_completed_keyboard()

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def show_repeat_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: Optional[str] = None,
    prefix_text: Optional[str] = None,
) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return

    topic = topic or get_saved_learn_topic(context)
    if not topic:
        await show_word_topics(update, context)
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        stats = get_topic_stats(db, user.id, user.level or "", topic)
        total_words = stats["total_words"]
        seen_word_ids = get_repeat_seen_word_ids(context)

        if total_words == 0:
            text = "В базе пока нет слов для этой темы. Запусти python seed_data.py."
            reply_markup = back_to_menu_keyboard()
        elif len(set(seen_word_ids)) >= total_words:
            await show_repeat_topic_completed(update, context, topic, prefix_text=prefix_text)
            return
        else:
            word = get_random_word_for_topic(db, user.level or "", topic, exclude_word_ids=seen_word_ids)
            if not word:
                await show_repeat_topic_completed(update, context, topic, prefix_text=prefix_text)
                return

            context.user_data["learn_topic"] = topic
            context.user_data["repeat_topic_mode"] = True
            context.user_data["current_word_id"] = word.id
            add_repeat_seen_word_id(context, word.id)
            text = format_repeat_word_card(word)
            reply_markup = learn_word_keyboard(word.id)

    if prefix_text:
        text = f"{prefix_text}\n\n{text}"

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def show_new_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: Optional[str] = None,
    exclude_word_id: Optional[int] = None,
    prefix_text: Optional[str] = None,
) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return
    topic = topic or get_saved_learn_topic(context)
    if not topic:
        await show_word_topics(update, context)
        return
    if is_repeat_topic_mode(context):
        await show_repeat_word(update, context, topic=topic, prefix_text=prefix_text)
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        if not user.level:
            text = "Сначала выбери уровень английского:"
            reply_markup = level_keyboard()
        elif count_words(db, user.level) == 0:
            text = "В базе пока нет слов для твоего уровня. Запусти python seed_data.py."
            reply_markup = back_to_menu_keyboard()
        else:
            word = get_random_new_word_for_user_by_topic(
                db=db,
                user_id=user.id,
                level=user.level,
                topic=topic,
                exclude_word_id=exclude_word_id,
            )
            if not word and exclude_word_id is not None:
                word = get_random_new_word_for_user_by_topic(
                    db=db,
                    user_id=user.id,
                    level=user.level,
                    topic=topic,
                )
            if not word:
                await show_topic_completed(update, context, topic, prefix_text=prefix_text)
                return
            else:
                context.user_data["learn_topic"] = topic
                context.user_data["current_word_id"] = word.id
                text = format_word_card(word)
                reply_markup = learn_word_keyboard(word.id)

        if prefix_text:
            text = f"{prefix_text}\n\n{text}"

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def learn_words_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not query.data or not telegram_user:
        return

    await query.answer()
    action = query.data

    if action in {"learn_words", "menu:words"}:
        context.user_data.clear()
        await show_word_topics(update, context)
        return

    if action == "learn_topics_back":
        context.user_data.pop("learn_topic", None)
        context.user_data.pop("repeat_topic_mode", None)
        context.user_data.pop("repeat_seen_word_ids", None)
        await show_word_topics(update, context)
        return

    if action == "repeat_topic":
        topic = get_saved_learn_topic(context)
        if not topic:
            await show_word_topics(update, context)
            return
        context.user_data["repeat_topic_mode"] = True
        context.user_data["repeat_seen_word_ids"] = []
        await show_repeat_word(update, context, topic=topic)
        return

    if action.startswith("learn_topic:"):
        topics = context.user_data.get("word_topics")
        if not isinstance(topics, list):
            await show_word_topics(update, context)
            return

        try:
            topic_index = int(action.split(":", maxsplit=1)[1])
            topic = topics[topic_index]
        except (IndexError, TypeError, ValueError):
            await show_word_topics(update, context)
            return

        context.user_data["learn_topic"] = topic
        context.user_data["repeat_topic_mode"] = False
        context.user_data.pop("repeat_seen_word_ids", None)
        await show_new_word(update, context, topic=topic)
        return

    if action == "next_word" or action.startswith("next_word:"):
        if is_repeat_topic_mode(context):
            await show_repeat_word(update, context, topic=get_saved_learn_topic(context))
            return

        exclude_word_id = context.user_data.get("current_word_id")
        if ":" in action:
            exclude_word_id = int(action.split(":", maxsplit=1)[1])
        topic = get_saved_learn_topic(context)
        if not topic and exclude_word_id:
            with SessionLocal() as db:
                word = get_word_by_id(db, exclude_word_id)
                topic = word.topic if word else None
            if topic:
                context.user_data["learn_topic"] = topic
        await show_new_word(update, context, topic=topic, exclude_word_id=exclude_word_id)
        return

    repeat_mode = is_repeat_topic_mode(context)

    if action == "word_known" or action.startswith("word_known:"):
        status = "known"
        if repeat_mode:
            prefix_text = "✅ Слово оставлено как знакомое.\n+5 XP"
        else:
            prefix_text = "✅ Отлично, слово отмечено как знакомое.\n+5 XP"
    elif action == "word_unknown" or action.startswith("word_learning:"):
        status = "learning"
        if repeat_mode:
            prefix_text = (
                "❌ Слово возвращено в заучивание.\n"
                "Оно попадётся в \"🧠 Заучивание\" и позже в \"🔁 Повторение\".\n"
                "+2 XP"
            )
        else:
            prefix_text = (
                "❌ Слово добавлено в заучивание.\n"
                "Оно появится в повторении через 5 минут после завершения заучивания.\n"
                "+2 XP"
            )
    else:
        return

    word_id = context.user_data.get("current_word_id")
    if ":" in action:
        word_id = int(action.split(":", maxsplit=1)[1])
    if not word_id:
        await show_word_topics(update, context)
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        word = get_word_by_id(db, int(word_id))
        if not word:
            await query.edit_message_text("Слово не найдено.", reply_markup=back_to_menu_keyboard())
            return
        topic = get_saved_learn_topic(context) or word.topic
        now = datetime.utcnow()
        user_word = db.scalar(
            select(UserWord).where(UserWord.user_id == user.id, UserWord.word_id == int(word_id))
        )

        if status == "known":
            if user_word:
                if repeat_mode:
                    user_word.status = "known"
                    user_word.correct_count += 1
                    user_word.review_streak = max(user_word.review_streak, 3)
                    user_word.is_learning_done = True
                    user_word.interval_days = 7
                    user_word.next_review_at = now + timedelta(days=7)
                    user_word.last_reviewed_at = now
                    add_user_xp(db, user, 5)
                else:
                    prefix_text = None
            else:
                user_word = UserWord(
                    user_id=user.id,
                    word_id=int(word_id),
                    status="known",
                    correct_count=1,
                    wrong_count=0,
                    learning_stage=0,
                    review_streak=0,
                    is_learning_done=True,
                    interval_days=7,
                    next_review_at=now + timedelta(days=7),
                    last_reviewed_at=now,
                )
                db.add(user_word)
                add_user_xp(db, user, 5)
        else:
            session_id = get_saved_learning_session(context, topic)
            if not session_id:
                session_id = get_active_learning_session_for_topic(db, user.id, topic)
            if not session_id:
                session_id = build_learning_session_id(user.id, topic or "general")
            context.user_data["learning_session_id"] = session_id
            context.user_data["learning_session_topic"] = topic

            if user_word:
                user_word.status = "learning"
                user_word.learning_stage = 0
                user_word.review_streak = 0
                user_word.is_learning_done = False
                user_word.learning_session_id = session_id
                user_word.wrong_count += 1
                user_word.interval_days = 0
                user_word.next_review_at = now + timedelta(minutes=5)
                user_word.last_reviewed_at = now
            else:
                user_word = UserWord(
                    user_id=user.id,
                    word_id=int(word_id),
                    status="learning",
                    correct_count=0,
                    wrong_count=1,
                    learning_stage=0,
                    review_streak=0,
                    learning_session_id=session_id,
                    is_learning_done=False,
                    interval_days=0,
                    next_review_at=now + timedelta(minutes=5),
                    last_reviewed_at=now,
                )
                db.add(user_word)
            add_user_xp(db, user, 2)
        db.commit()

    if topic:
        context.user_data["learn_topic"] = topic
    if repeat_mode:
        await show_repeat_word(update, context, topic=topic, prefix_text=prefix_text)
        return
    await show_new_word(update, context, topic=topic, exclude_word_id=int(word_id), prefix_text=prefix_text)


async def debug_words_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message:
        return

    topic = get_saved_learn_topic(context)
    repeat_mode = is_repeat_topic_mode(context)

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        stats = None
        if topic and user.level:
            stats = get_topic_stats(db, user.id, user.level, topic)

        lines = [
            f"User level: {user.level}",
            f"Current topic: {topic or 'нет'}",
            f"Repeat topic mode: {repeat_mode}",
        ]
        if stats:
            lines.extend(
                [
                    f"Topic total words: {stats['total_words']}",
                    f"Topic user words: {stats['user_words_in_topic']}",
                    f"Topic known: {stats['known_count']}",
                    f"Topic learning: {stats['learning_count']}",
                    f"Topic review: {stats['review_count']}",
                ]
            )
        else:
            lines.extend(
                [
                    "Topic total words: 0",
                    "Topic user words: 0",
                    "Topic known: 0",
                    "Topic learning: 0",
                    "Topic review: 0",
                ]
            )

    await message.reply_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
