from telegram import Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import level_keyboard, main_menu_keyboard
from services.user_service import get_or_create_user, set_user_level


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    if not telegram_user or not update.effective_message:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)

    if not user.level:
        await update.effective_message.reply_text(
            "Привет! Давай подберем уровень английского. Выбери A1, A2, B1 или B2:",
            reply_markup=level_keyboard(),
        )
        return

    await update.effective_message.reply_text(
        f"С возвращением! Твой уровень: {user.level}.",
        reply_markup=main_menu_keyboard(),
    )


async def level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user or not query.data:
        return

    await query.answer()
    context.user_data.clear()
    level = query.data.split(":", maxsplit=1)[1]

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        set_user_level(db, user.telegram_id, level)

    await query.edit_message_text(
        f"Уровень обновлен: {level}. Главное меню:",
        reply_markup=main_menu_keyboard(),
    )
