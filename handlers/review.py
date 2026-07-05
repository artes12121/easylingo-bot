from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import back_to_menu_keyboard, level_keyboard, no_reviews_keyboard, review_answer_keyboard
from models import UserWord
from services.review_service import get_next_due_review, get_user_word, update_review_result
from services.user_service import add_user_xp, get_or_create_user
from services.word_format_service import format_word_card, format_word_question, get_word_translation


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_review(update, context)


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


def format_review_question(user_word: UserWord) -> str:
    return format_word_question(user_word.word, header="🔁 Повторение")


def format_days(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return f"{days} день"
    if days % 10 in {2, 3, 4} and days % 100 not in {12, 13, 14}:
        return f"{days} дня"
    return f"{days} дней"


def format_review_result(user_word: UserWord, is_correct: bool, user_answer: str, status_before: str) -> str:
    word = user_word.word
    if is_correct:
        if status_before == "learning":
            if user_word.status == "review":
                progress_text = "3 / 3 правильных ответов.\n🎉 Слово вернулось в повторение."
            else:
                progress_text = (
                    f"{user_word.learning_stage} / 3 правильных ответов.\n"
                    "Следующая проверка через: 5 минут."
                )
        elif user_word.status == "known":
            progress_text = (
                f"{user_word.review_streak} / 3 правильных повторений.\n"
                "🎉 Слово закреплено!"
            )
        else:
            progress_text = (
                f"{user_word.review_streak} / 3 правильных повторений.\n"
                "Следующее повторение через: 5 минут."
            )

        return (
            "✅ Верно!\n"
            f"{format_word_card(word)}\n\n"
            f"{progress_text}\n"
            "+5 XP"
        )

    return (
        "❌ Неверно.\n\n"
        "Правильный ответ:\n"
        f"{format_word_card(word)}\n\n"
        "Твой ответ:\n"
        f"{user_answer}\n\n"
        "Слово вернулось в заучивание.\n"
        "Чтобы закрепить его, нужно ответить правильно 3 раза подряд.\n"
        "+1 XP"
    )


async def start_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user:
        return

    if query:
        await query.answer()

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        if not user.level:
            text = "Сначала выбери уровень английского:"
            reply_markup = level_keyboard()
        else:
            user_word = get_next_due_review(db, user.id)
            if not user_word:
                context.user_data.pop("state", None)
                context.user_data.pop("review_user_word_id", None)
                text = "Сегодня слов для повторения нет ✅\nМожешь выучить новые слова."
                reply_markup = no_reviews_keyboard()
            else:
                context.user_data["state"] = "waiting_review_answer"
                context.user_data["review_user_word_id"] = user_word.id
                text = format_review_question(user_word)
                reply_markup = back_to_menu_keyboard()

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


async def review_words_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_review(update, context)


async def review_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("state") == "waiting_learning_answer":
        from handlers.learning import learning_answer_handler

        await learning_answer_handler(update, context)
        return

    if context.user_data.get("state") == "translator":
        from handlers.translator import translator_text_handler

        await translator_text_handler(update, context)
        return

    if context.user_data.get("state") != "waiting_review_answer":
        return

    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message or not message.text:
        return

    user_word_id = context.user_data.get("review_user_word_id")
    if not user_word_id:
        context.user_data.clear()
        await message.reply_text("Не нашел слово для проверки.", reply_markup=back_to_menu_keyboard())
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        user_word = get_user_word(db, user.id, int(user_word_id))
        if not user_word:
            context.user_data.clear()
            await message.reply_text("Слово для повторения не найдено.", reply_markup=back_to_menu_keyboard())
            return

        is_correct = is_correct_translation(message.text, get_word_translation(user_word.word))
        status_before = user_word.status
        update_review_result(user_word, is_correct)
        add_user_xp(db, user, 5 if is_correct else 1)
        if not is_correct and user_word.learning_session_id:
            context.user_data["learning_session_id"] = user_word.learning_session_id
            context.user_data["learning_session_topic"] = user_word.word.topic
        db.commit()
        text = format_review_result(user_word, is_correct, message.text, status_before)

    context.user_data.pop("state", None)
    context.user_data.pop("review_user_word_id", None)
    await message.reply_text(text, reply_markup=review_answer_keyboard())
