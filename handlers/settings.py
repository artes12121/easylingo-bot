from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import level_keyboard, reset_progress_confirm_keyboard, settings_keyboard
from services.user_service import get_or_create_user, reset_user_progress


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_text(
            await build_settings_text(update),
            reply_markup=settings_keyboard(),
        )


async def build_settings_text(update: Update) -> str:
    telegram_user = update.effective_user
    if not telegram_user:
        return "⚙️ Настройки"

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        level = user.level or "не выбран"
        language = user.target_language

    return (
        "⚙️ Настройки\n\n"
        f"Текущий уровень: {level}\n"
        f"Язык: {language}"
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not query.data or not telegram_user:
        return

    await query.answer()
    context.user_data.clear()
    action = query.data

    if action in {"settings", "menu:settings"}:
        await query.edit_message_text(await build_settings_text(update), reply_markup=settings_keyboard())
        return

    if action == "change_level":
        await query.edit_message_text("Выбери новый уровень:", reply_markup=level_keyboard())
        return

    if action == "reset_progress":
        await query.edit_message_text(
            "Ты точно хочешь сбросить прогресс?",
            reply_markup=reset_progress_confirm_keyboard(),
        )
        return

    if action == "cancel_reset_progress":
        await query.edit_message_text(await build_settings_text(update), reply_markup=settings_keyboard())
        return

    if action == "confirm_reset_progress":
        with SessionLocal() as db:
            user = get_or_create_user(db, telegram_user)
            reset_user_progress(db, user)
            db.commit()

        await query.edit_message_text(
            "Прогресс сброшен.",
            reply_markup=settings_keyboard(),
        )
