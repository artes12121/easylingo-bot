from datetime import datetime, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import (
    back_to_menu_keyboard,
    learning_answer_keyboard,
    learning_card_keyboard,
    learning_complete_keyboard,
    learning_empty_keyboard,
)
from models import UserWord
from services.learning_service import (
    build_learning_session_id,
    complete_learning_session,
    count_learning_done,
    count_learning_words,
    get_active_learning_session_id,
    get_debug_learning_words,
    get_next_learning_word,
)
from services.review_service import count_due_reviews, get_user_word
from services.user_service import add_user_xp, get_or_create_user
from services.word_format_service import format_word_card, format_word_question, get_word_translation


def normalize_answer(value: str) -> str:
    cleaned = value.lower().strip()
    for char in ".,!?":
        cleaned = cleaned.replace(char, "")
    return " ".join(cleaned.split())


def is_correct_translation(answer: str, russian: str) -> bool:
    normalized_answer = normalize_answer(answer)
    variants = {normalize_answer(russian)}
    variants.update(normalize_answer(part) for part in russian.split(","))
    variants.discard("")
    return normalized_answer in variants


def format_learning_question(user_word: UserWord) -> str:
    return format_word_question(user_word.word, header="🧠 Заучивание")


def format_learning_success(user_word: UserWord, remaining_count: int) -> str:
    word = user_word.word
    return (
        "✅ Верно!\n\n"
        f"{format_word_card(word)}\n\n"
        "+5 XP\n\n"
        f"Осталось слов в заучивании: {remaining_count}."
    )


def format_learning_wrong(user_word: UserWord, user_answer: str) -> str:
    word = user_word.word
    return (
        "❌ Неверно.\n\n"
        "Правильный ответ:\n"
        f"{format_word_card(word)}\n\n"
        "Твой ответ:\n"
        f"{user_answer}\n\n"
        "Слово остаётся в заучивании и попадётся снова.\n"
        "+1 XP"
    )


def format_learning_complete() -> str:
    return (
        "🎉 Заучивание завершено!\n\n"
        "Ты правильно ответил на все слова этой пачки.\n"
        "Эти слова появятся в повторении через 5 минут."
    )


async def show_learning_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    exclude_user_word_id: Optional[int] = None,
) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        session_id = context.user_data.get("learning_session_id")
        if not isinstance(session_id, str) or not session_id:
            session_id = None

        user_word = None
        if session_id:
            user_word = get_next_learning_word(
                db,
                user.id,
                learning_session_id=session_id,
                exclude_user_word_id=exclude_user_word_id,
            )
            if not user_word and exclude_user_word_id is not None:
                user_word = get_next_learning_word(db, user.id, learning_session_id=session_id)

        if not user_word:
            session_id = get_active_learning_session_id(db, user.id)
            if session_id:
                context.user_data["learning_session_id"] = session_id
            user_word = get_next_learning_word(
                db,
                user.id,
                learning_session_id=session_id,
                exclude_user_word_id=exclude_user_word_id,
            )
            if not user_word and exclude_user_word_id is not None:
                user_word = get_next_learning_word(db, user.id, learning_session_id=session_id)

        if not user_word:
            context.user_data.pop("state", None)
            context.user_data.pop("learning_user_word_id", None)
            context.user_data.pop("learning_session_id", None)
            text = (
                "🧠 Заучивание\n\n"
                "Сейчас нет слов для заучивания.\n"
                "Выбери тему в \"📚 Учить слова\" и нажимай \"❌ Не знаю\" на незнакомых словах."
            )
            reply_markup = learning_empty_keyboard()
        else:
            if user_word.learning_session_id:
                context.user_data["learning_session_id"] = user_word.learning_session_id
                context.user_data["learning_session_topic"] = user_word.word.topic
            context.user_data["state"] = "waiting_learning_answer"
            context.user_data["learning_user_word_id"] = user_word.id
            text = format_learning_question(user_word)
            reply_markup = learning_card_keyboard(user_word.id)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def learning_drill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    exclude_user_word_id = None
    if query and query.data == "learning_next":
        raw_id = context.user_data.get("learning_user_word_id")
        if raw_id:
            exclude_user_word_id = int(raw_id)

    if query and query.data and query.data.startswith("learning_check:"):
        context.user_data["learning_user_word_id"] = int(query.data.split(":", maxsplit=1)[1])

    await show_learning_word(update, context, exclude_user_word_id=exclude_user_word_id)


async def learning_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("state") != "waiting_learning_answer":
        return

    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message or not message.text:
        return

    user_word_id = context.user_data.get("learning_user_word_id")
    if not user_word_id:
        context.user_data.pop("state", None)
        await message.reply_text("Не нашел слово для проверки.", reply_markup=back_to_menu_keyboard())
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        user_word = get_user_word(db, user.id, int(user_word_id))
        if not user_word:
            context.user_data.pop("state", None)
            await message.reply_text("Слово для заучивания не найдено.", reply_markup=back_to_menu_keyboard())
            return

        now = datetime.utcnow()
        word = user_word.word
        session_id = user_word.learning_session_id or context.user_data.get("learning_session_id")
        if not isinstance(session_id, str) or not session_id:
            session_id = build_learning_session_id(user.id, word.topic or "general")
        user_word.learning_session_id = session_id
        context.user_data["learning_session_id"] = session_id
        context.user_data["learning_session_topic"] = word.topic

        is_correct = is_correct_translation(message.text, get_word_translation(word))
        is_complete = False

        if is_correct:
            user_word.correct_count += 1
            user_word.learning_stage += 1
            user_word.is_learning_done = True
            user_word.status = "learning"
            user_word.interval_days = 0
            user_word.next_review_at = now + timedelta(minutes=5)
            user_word.last_reviewed_at = now
            add_user_xp(db, user, 5)

            remaining_count = count_learning_words(
                db,
                user.id,
                learning_session_id=session_id,
                only_not_done=True,
            )
            if remaining_count == 0:
                complete_learning_session(db, user.id, session_id, now)
                text = format_learning_complete()
                reply_markup = learning_complete_keyboard()
                is_complete = True
            else:
                text = format_learning_success(user_word, remaining_count)
                reply_markup = learning_answer_keyboard()
        else:
            user_word.wrong_count += 1
            user_word.learning_stage = 0
            user_word.is_learning_done = False
            user_word.status = "learning"
            user_word.interval_days = 0
            user_word.next_review_at = now + timedelta(minutes=5)
            user_word.last_reviewed_at = now
            add_user_xp(db, user, 1)
            text = format_learning_wrong(user_word, message.text)
            reply_markup = learning_answer_keyboard()

        db.commit()

    context.user_data.pop("state", None)
    context.user_data.pop("learning_user_word_id", None)
    if is_complete:
        context.user_data.pop("learning_session_id", None)
        context.user_data.pop("learning_session_topic", None)

    await message.reply_text(text, reply_markup=reply_markup)


async def debug_learning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        active_session = context.user_data.get("learning_session_id")
        if not isinstance(active_session, str) or not active_session:
            active_session = get_active_learning_session_id(db, user.id)

        learning_total = db.query(UserWord).filter(UserWord.user_id == user.id, UserWord.status == "learning").count()
        learning_not_done = (
            db.query(UserWord)
            .filter(
                UserWord.user_id == user.id,
                UserWord.status == "learning",
                UserWord.is_learning_done.is_(False),
            )
            .count()
        )
        learning_done = (
            db.query(UserWord)
            .filter(
                UserWord.user_id == user.id,
                UserWord.status == "learning",
                UserWord.is_learning_done.is_(True),
            )
            .count()
        )
        review_total = db.query(UserWord).filter(UserWord.user_id == user.id, UserWord.status == "review").count()
        known = db.query(UserWord).filter(UserWord.user_id == user.id, UserWord.status == "known").count()
        due_now = count_due_reviews(db, user.id)
        current_session_words = get_debug_learning_words(db, user.id, learning_session_id=active_session)

        lines = [
            f"User level: {user.level}",
            f"Active learning session: {active_session or 'нет'}",
            f"Learning total: {learning_total}",
            f"Learning not done: {learning_not_done}",
            f"Learning done: {learning_done}",
            f"Review total: {review_total}",
            f"Due now: {due_now}",
            f"Known: {known}",
            "",
            "Current session words:",
        ]
        if current_session_words:
            for user_word in current_session_words:
                lines.append(
                    "- "
                    f"{user_word.word.english} / {get_word_translation(user_word.word)} / "
                    f"done={bool(user_word.is_learning_done)} / "
                    f"stage={user_word.learning_stage} / "
                    f"review_streak={user_word.review_streak}"
                )
        else:
            lines.append("- нет")

    await message.reply_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
