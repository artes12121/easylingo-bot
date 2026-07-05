from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import back_to_menu_keyboard, level_keyboard, main_menu_keyboard
from services.grammar_service import get_grammar_stats
from services.learning_service import get_learning_stats
from services.review_service import get_user_word_stats
from services.user_service import get_or_create_user


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_text("Главное меню:", reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Команды: /start - начать, /menu - открыть меню, /help - помощь.",
            reply_markup=main_menu_keyboard(),
        )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    action = query.data
    if action.startswith("menu:"):
        action = action.split(":", maxsplit=1)[1]

    if action in {"main_menu", "main"}:
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())
        return

    if action == "words":
        from handlers.words import learn_words_callback

        await learn_words_callback(update, context)
        return

    if action == "review":
        from handlers.review import review_words_callback

        await review_words_callback(update, context)
        return

    if action == "progress":
        await progress_callback(update, context)
        return

    if action == "settings":
        from handlers.settings import settings_callback

        await settings_callback(update, context)
        return

    if action == "grammar":
        from handlers.grammar import grammar_menu_callback

        await grammar_menu_callback(update, context)
        return

    if action == "translator":
        from handlers.translator import translator_callback

        await translator_callback(update, context)
        return

    await query.answer()
    await query.edit_message_text(
        "Переводчик будет добавлен следующим этапом.",
        reply_markup=back_to_menu_keyboard(),
    )


async def progress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    await query.answer()
    active_session_id = context.user_data.get("learning_session_id")
    if not isinstance(active_session_id, str) or not active_session_id:
        active_session_id = None
    context.user_data.pop("state", None)
    context.user_data.pop("review_user_word_id", None)
    context.user_data.pop("learning_user_word_id", None)

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        if not user.level:
            await query.edit_message_text(
                "Сначала выбери уровень английского:",
                reply_markup=level_keyboard(),
            )
            return

        stats = get_user_word_stats(db, user.id)
        learning_stats = get_learning_stats(db, user.id, active_session_id)
        grammar_stats = get_grammar_stats(db, user.id)
        text = (
            "📊 Твой прогресс\n\n"
            f"Язык: {user.target_language}\n"
            f"Уровень: {user.level}\n"
            f"XP: {user.xp}\n\n"
            "📚 Слова:\n"
            f"Добавлено в обучение: {stats['learned_words']}\n"
            f"Знакомые: {stats['known_words']}\n"
            f"На заучивании: {stats['learning_words']}\n"
            f"К повторению сейчас: {stats['due_reviews']}\n"
            f"Правильных ответов по словам: {stats['correct_answers']}\n"
            f"Ошибок по словам: {stats['wrong_answers']}\n\n"
            "🧠 Заучивание:\n"
            f"Активных слов: {learning_stats['learning_not_done']}\n"
            f"Закрыто в текущей сессии: {learning_stats['current_session_done']}\n"
            f"Осталось в текущей сессии: {learning_stats['current_session_not_done']}\n\n"
            "🔁 Повторение:\n"
            f"К повторению сейчас: {stats['due_reviews']}\n"
            f"Закреплено слов: {stats['known_words']}\n"
            f"Слов с серией 1/3: {stats['review_streak_1']}\n"
            f"Слов с серией 2/3: {stats['review_streak_2']}\n\n"
            "📝 Грамматика:\n"
            f"Уроков открыто: {grammar_stats['total']}\n"
            f"Уроков завершено: {grammar_stats['completed']}\n"
            f"Правильных ответов: {grammar_stats['correct']}\n"
            f"Ошибок: {grammar_stats['wrong']}"
        )

    await query.edit_message_text(text, reply_markup=back_to_menu_keyboard())
