from __future__ import annotations

import logging

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN,
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_GET_UPDATES_READ_TIMEOUT,
    TELEGRAM_POOL_TIMEOUT,
    TELEGRAM_PROXY_URL,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
)
from database import init_db
from handlers.grammar import (
    grammar_answer_callback,
    grammar_command,
    grammar_level_callback,
    grammar_lesson_callback,
    grammar_lesson_explain_callback,
    grammar_lessons_callback,
    grammar_levels_callback,
    grammar_menu_callback,
    grammar_next_lesson_callback,
    grammar_next_question_callback,
    grammar_random_callback,
    grammar_section_callback,
    grammar_test_callback,
    grammar_topic_callback,
    grammar_topics_callback,
)
from handlers.learning import debug_learning_command, learning_drill_callback
from handlers.menu import help_command, menu_callback, menu_command, progress_callback
from handlers.review import review_answer_handler, review_command, review_words_callback
from handlers.settings import settings_callback, settings_command
from handlers.start import level_callback, start_command
from handlers.translator import translator_callback, translator_command
from handlers.words import debug_words_command, learn_words_callback, words_command


logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, (TimedOut, NetworkError)):
        logger.warning("Сетевая ошибка Telegram: %s", error)
        return

    logger.exception("Unhandled bot error", exc_info=error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Попробуй ещё раз или открой /menu."
        )


def build_application():
    request_kwargs = {}
    if TELEGRAM_PROXY_URL:
        request_kwargs["proxy"] = TELEGRAM_PROXY_URL

    request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        **request_kwargs,
    )
    get_updates_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_GET_UPDATES_READ_TIMEOUT,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        **request_kwargs,
    )

    return (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )


def main() -> None:
    if not BOT_TOKEN:
        print("BOT_TOKEN не найден. Укажи BOT_TOKEN в .env")
        return

    init_db()

    application = build_application()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("words", words_command))
    application.add_handler(CommandHandler("review", review_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("grammar", grammar_command))
    application.add_handler(CommandHandler("translator", translator_command))
    application.add_handler(CommandHandler("debug_learning", debug_learning_command))
    application.add_handler(CommandHandler("debug_words", debug_words_command))
    application.add_handler(CallbackQueryHandler(level_callback, pattern=r"^level:"))
    application.add_handler(
        CallbackQueryHandler(
            learn_words_callback,
            pattern=(
                r"^(learn_words|menu:words|learn_topics_back|learn_topic:\d+|"
                r"repeat_topic|next_word(?::\d+)?|word_known(?::\d+)?|word_unknown|word_learning:\d+)$"
            ),
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            learning_drill_callback,
            pattern=r"^(learning_drill|learning_next|learning_check:\d+)$",
        )
    )
    application.add_handler(CallbackQueryHandler(review_words_callback, pattern=r"^(review_words|menu:review)$"))
    application.add_handler(CallbackQueryHandler(progress_callback, pattern=r"^(progress|menu:progress)$"))
    application.add_handler(
        CallbackQueryHandler(
            settings_callback,
            pattern=r"^(settings|menu:settings|change_level|reset_progress|confirm_reset_progress|cancel_reset_progress)$",
        )
    )
    application.add_handler(CallbackQueryHandler(grammar_menu_callback, pattern=r"^(grammar|menu:grammar)$"))
    application.add_handler(CallbackQueryHandler(grammar_random_callback, pattern=r"^grammar_random$"))
    application.add_handler(CallbackQueryHandler(grammar_levels_callback, pattern=r"^grammar_levels$"))
    application.add_handler(CallbackQueryHandler(grammar_level_callback, pattern=r"^grammar_level:(A1|A2|B1|B2)$"))
    application.add_handler(
        CallbackQueryHandler(grammar_section_callback, pattern=r"^grammar_section:(A1|A2|B1|B2):[a-z_]+$")
    )
    application.add_handler(CallbackQueryHandler(grammar_lessons_callback, pattern=r"^grammar_lessons$"))
    application.add_handler(CallbackQueryHandler(grammar_topics_callback, pattern=r"^grammar_topics$"))
    application.add_handler(CallbackQueryHandler(grammar_topic_callback, pattern=r"^grammar_topic:\d+$"))
    application.add_handler(CallbackQueryHandler(grammar_lesson_callback, pattern=r"^grammar_lesson:\d+$"))
    application.add_handler(CallbackQueryHandler(grammar_test_callback, pattern=r"^grammar_test:\d+$"))
    application.add_handler(CallbackQueryHandler(grammar_next_lesson_callback, pattern=r"^grammar_next_lesson:\d+$"))
    application.add_handler(CallbackQueryHandler(grammar_next_question_callback, pattern=r"^grammar_next_question$"))
    application.add_handler(CallbackQueryHandler(grammar_lesson_explain_callback, pattern=r"^grammar_lesson_explain$"))
    application.add_handler(CallbackQueryHandler(grammar_answer_callback, pattern=r"^grammar_answer:\d+:\d+:\d+$"))
    application.add_handler(
        CallbackQueryHandler(
            translator_callback,
            pattern=r"^(translator|menu:translator|translator_again|translator_back|translator_mode:(auto|en_ru|ru_en))$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^(main_menu|menu:main)$",
        )
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, review_answer_handler))
    application.add_error_handler(error_handler)

    print("Бот запущен. Нажми Ctrl+C для остановки.")
    if TELEGRAM_PROXY_URL:
        print("Используется прокси для Telegram API.")
    application.run_polling(drop_pending_updates=True, bootstrap_retries=-1)


if __name__ == "__main__":
    main()
