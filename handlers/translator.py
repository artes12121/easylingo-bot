from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import main_menu_keyboard, translator_intro_keyboard, translator_result_keyboard
from models import TranslationHistory
from services.translator_service import (
    TranslatorAPIError,
    TranslatorAuthError,
    TranslatorConfigError,
    TranslatorRateLimitError,
    is_translator_configured,
    translate_text,
)
from services.user_service import get_or_create_user


logger = logging.getLogger(__name__)
translator_modes: dict[int, str] = {}

MODE_LABELS = {
    "auto": "Автоопределение",
    "en_ru": "EN → RU",
    "ru_en": "RU → EN",
}


def get_translator_mode(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    mode = context.user_data.get("translator_mode") or translator_modes.get(user_id) or "auto"
    if mode not in MODE_LABELS:
        return "auto"
    return str(mode)


def set_translator_mode(user_id: int, context: ContextTypes.DEFAULT_TYPE, mode: str) -> str:
    if mode not in MODE_LABELS:
        mode = "auto"
    translator_modes[user_id] = mode
    context.user_data["translator_mode"] = mode
    context.user_data["state"] = "translator"
    return mode


def translator_intro_text() -> str:
    return (
        "🌍 Переводчик\n\n"
        "Отправь слово, фразу или предложение.\n"
        "Я переведу и кратко разберу.\n\n"
        "Примеры:\n"
        "• I have been working all day.\n"
        "• Мне нужно записаться к врачу.\n"
        "• get over"
    )


async def translator_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message:
        return

    set_translator_mode(telegram_user.id, context, get_translator_mode(telegram_user.id, context))
    await message.reply_text(translator_intro_text(), reply_markup=translator_intro_keyboard())


async def translator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not query.data or not telegram_user:
        return

    await query.answer()
    action = query.data

    if action in {"translator", "menu:translator"}:
        set_translator_mode(telegram_user.id, context, get_translator_mode(telegram_user.id, context))
        await query.edit_message_text(translator_intro_text(), reply_markup=translator_intro_keyboard())
        return

    if action == "translator_back":
        context.user_data.clear()
        await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())
        return

    if action == "translator_again":
        context.user_data["state"] = "translator"
        await query.edit_message_text(
            "Отправь следующий текст для перевода.",
            reply_markup=translator_intro_keyboard(),
        )
        return

    if action.startswith("translator_mode:"):
        mode = action.split(":", maxsplit=1)[1]
        mode = set_translator_mode(telegram_user.id, context, mode)
        await query.edit_message_text(
            f"Режим перевода изменён: {MODE_LABELS[mode]}\nОтправь текст.",
            reply_markup=translator_intro_keyboard(),
        )


async def translator_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("state") != "translator":
        return

    telegram_user = update.effective_user
    message = update.effective_message
    if not telegram_user or not message or message.text is None:
        return

    source_text = message.text.strip()
    if not source_text:
        await message.reply_text(
            "Отправь слово, фразу или предложение для перевода.",
            reply_markup=translator_intro_keyboard(),
        )
        return

    if len(source_text) > 3000:
        await message.reply_text(
            "Слишком длинный текст. Отправь, пожалуйста, до 3000 символов.",
            reply_markup=translator_intro_keyboard(),
        )
        return

    if not is_translator_configured():
        await message.reply_text(
            "⚠️ Yandex Translate не настроен.\n"
            "Добавь YANDEX_TRANSLATE_API_KEY и YANDEX_FOLDER_ID в .env",
            reply_markup=translator_intro_keyboard(),
        )
        return

    mode = get_translator_mode(telegram_user.id, context)

    try:
        result = await translate_text(source_text, mode=mode)
    except TranslatorConfigError:
        await message.reply_text(
            "⚠️ Yandex Translate не настроен.\n"
            "Добавь YANDEX_TRANSLATE_API_KEY и YANDEX_FOLDER_ID в .env",
            reply_markup=translator_intro_keyboard(),
        )
        return
    except TranslatorAuthError as error:
        logger.warning("Yandex Translate auth error: %s", error)
        await message.reply_text(
            "⚠️ Ошибка авторизации Yandex Translate.\n"
            "Проверь API key и права сервисного аккаунта.",
            reply_markup=translator_result_keyboard(),
        )
        return
    except TranslatorRateLimitError as error:
        logger.warning("Yandex Translate rate limit error: %s", error)
        await message.reply_text(
            "⚠️ Слишком много запросов к Yandex Translate.\nПопробуй позже.",
            reply_markup=translator_result_keyboard(),
        )
        return
    except TranslatorAPIError as error:
        logger.warning("Yandex Translate API error: %s", error)
        await message.reply_text(
            "⚠️ Ошибка Yandex Translate.\nПопробуй позже.",
            reply_markup=translator_result_keyboard(),
        )
        return
    except Exception as error:
        logger.exception("Unexpected translator error: %s", error)
        await message.reply_text(
            "⚠️ Ошибка Yandex Translate.\nПопробуй позже.",
            reply_markup=translator_result_keyboard(),
        )
        return

    if not result:
        result = "⚠️ Не получилось перевести.\nПопробуй ещё раз через несколько секунд."

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        db.add(
            TranslationHistory(
                user_id=user.id,
                source_text=source_text,
                translated_text=result,
                mode=mode,
                direction=mode,
            )
        )
        db.commit()

    context.user_data["state"] = "translator"
    await message.reply_text(result, reply_markup=translator_result_keyboard())
