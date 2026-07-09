from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database import SessionLocal
from keyboards import (
    back_to_menu_keyboard,
    grammar_after_answer_keyboard,
    grammar_lesson_keyboard,
    grammar_question_keyboard,
)
from models import GrammarLesson
from services.grammar_service import (
    GRAMMAR_LEVELS,
    get_grammar_section_id,
    get_grammar_section_label,
    get_grammar_sections_for_level,
    get_lesson_by_callback_value,
    get_lesson_common_mistakes,
    get_lesson_examples,
    get_lesson_progress,
    get_lesson_questions,
    get_lessons_by_section,
    get_lessons_by_level,
    get_next_lesson,
    lesson_progress_percent,
    mark_lesson_seen,
    save_lesson_answer,
)
from services.user_service import add_user_xp, get_or_create_user


def safe_text(value: object) -> str:
    return str(value or "").strip()


def solved_sentence(question: str, correct_answer: str) -> str:
    if "___" in question:
        return question.replace("___", correct_answer)
    return correct_answer


def trim_text(text: str, limit: int = 3900) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 80].rstrip() + "\n\n..."


def format_lesson_text(lesson: GrammarLesson) -> str:
    examples = get_lesson_examples(lesson)
    common_mistakes = get_lesson_common_mistakes(lesson)

    parts = [
        f"📘 Урок {lesson.unit}: {lesson.title_ru}",
        "",
        lesson.explanation_ru,
    ]

    if lesson.formula:
        parts.extend(["", "Формула:", lesson.formula])

    if examples:
        parts.extend(["", "Примеры:"])
        for index, example in enumerate(examples, start=1):
            note = safe_text(example.get("note"))
            block = [
                f"{index}. {safe_text(example.get('en'))}",
                safe_text(example.get("ru")),
            ]
            if note:
                block.append(f"Пояснение: {note}")
            parts.append("\n".join(block))

    if common_mistakes:
        parts.extend(["", "Типичные ошибки:"])
        for mistake in common_mistakes:
            parts.append(
                "\n".join(
                    [
                        f"❌ {safe_text(mistake.get('wrong'))}",
                        f"✅ {safe_text(mistake.get('correct'))}",
                        f"Почему: {safe_text(mistake.get('explanation'))}",
                    ]
                )
            )

    return trim_text("\n".join(parts))


def format_question_text(lesson: GrammarLesson, question_index: int) -> tuple[str, list[str], dict]:
    questions = get_lesson_questions(lesson)
    question = questions[question_index]
    options = question.get("options") if isinstance(question.get("options"), list) else []
    text = (
        f"🧪 Тест: {lesson.title_ru}\n\n"
        f"Вопрос {question_index + 1}/{len(questions)}:\n"
        f"{safe_text(question.get('question'))}\n\n"
    )
    letters = ["A", "B", "C", "D", "E", "F"]
    text += "\n".join(f"{letters[index]}) {option}" for index, option in enumerate(options))
    return text, [safe_text(option) for option in options], question


async def grammar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await show_grammar_entry(update, context)


async def grammar_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    context.user_data.clear()
    await show_grammar_entry(update, context)


async def show_grammar_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    if telegram_user:
        with SessionLocal() as db:
            user = get_or_create_user(db, telegram_user)
            if user.level:
                await show_grammar_sections(update, context, user.level)
                return

    await show_grammar_levels(update, context)


async def show_grammar_levels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    message = update.effective_message

    context.user_data.pop("grammar_level", None)
    context.user_data.pop("grammar_section_id", None)
    context.user_data.pop("grammar_lesson_units", None)
    context.user_data.pop("grammar_lesson_unit", None)
    context.user_data.pop("grammar_question_index", None)
    text = "📝 Грамматика\n\nВыбери уровень:"
    reply_markup = grammar_levels_keyboard()

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


def grammar_levels_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(label, callback_data=f"grammar_level:{level}")] for level, label in GRAMMAR_LEVELS]
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def show_grammar_sections(update: Update, context: ContextTypes.DEFAULT_TYPE, level: str) -> None:
    query = update.callback_query
    message = update.effective_message

    with SessionLocal() as db:
        sections = get_grammar_sections_for_level(db, level)

    context.user_data["grammar_level"] = level
    context.user_data.pop("grammar_section_id", None)
    context.user_data.pop("grammar_lesson_units", None)
    context.user_data.pop("grammar_lesson_unit", None)
    context.user_data.pop("grammar_question_index", None)

    if not sections:
        text = (
            f"📝 Грамматика · {level}\n\n"
            "В базе пока нет уроков грамматики для этого уровня.\n"
            "Запусти python seed_data.py."
        )
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⬅️ К уровням", callback_data="grammar_levels")],
                [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
            ]
        )
    else:
        text = f"📝 Грамматика · {level}\n\nВыбери раздел:"
        reply_markup = grammar_sections_keyboard(level, sections)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


def grammar_sections_keyboard(level: str, sections: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"grammar_section:{level}:{section_id}")]
        for section_id, label in sections
    ]
    rows.append([InlineKeyboardButton("⬅️ К уровням", callback_data="grammar_levels")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def show_section_lessons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    level: str,
    section_id: str,
) -> None:
    query = update.callback_query
    message = update.effective_message
    telegram_user = update.effective_user
    if not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        lessons = get_lessons_by_section(db, level, section_id)
        section_label = get_grammar_section_label(level, section_id)

        if not lessons:
            text = f"📚 {level} · {section_label}\n\nВ этом разделе пока нет уроков."
            reply_markup = grammar_section_empty_keyboard(level)
        else:
            lines = [f"📚 {level} · {section_label}", ""]
            for index, lesson in enumerate(lessons, start=1):
                progress = get_lesson_progress(db, user.id, lesson.unit)
                percent = lesson_progress_percent(progress, lesson)
                suffix = f" — {percent}%" if percent else ""
                lines.append(f"{index}. {lesson.title_ru}{suffix}")
            text = trim_text("\n".join(lines))
            reply_markup = grammar_section_lessons_keyboard(level, lessons)

    context.user_data["grammar_level"] = level
    context.user_data["grammar_section_id"] = section_id
    context.user_data["grammar_lesson_units"] = [lesson.unit for lesson in lessons]

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, reply_markup=reply_markup)


def grammar_section_lessons_keyboard(level: str, lessons: list[GrammarLesson]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for index, lesson in enumerate(lessons, start=1):
        row.append(InlineKeyboardButton(str(index), callback_data=f"grammar_lesson:{lesson.unit}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.extend(grammar_section_back_rows(level))
    return InlineKeyboardMarkup(rows)


def grammar_section_empty_keyboard(level: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(grammar_section_back_rows(level))


def grammar_section_back_rows(level: str) -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("⬅️ К разделам", callback_data=f"grammar_level:{level}")],
        [InlineKeyboardButton("⬅️ К уровням", callback_data="grammar_levels")],
        [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
    ]


def get_current_grammar_location(context: ContextTypes.DEFAULT_TYPE) -> tuple[str | None, str | None]:
    return (
        context.user_data.get("grammar_level"),
        context.user_data.get("grammar_section_id"),
    )


async def show_current_lessons_or_levels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    level, section_id = get_current_grammar_location(context)
    if level and section_id:
        await show_section_lessons(update, context, level, section_id)
        return
    if level:
        await show_grammar_sections(update, context, level)
        return
    await show_grammar_levels(update, context)


def lesson_section_id(lesson: GrammarLesson) -> str:
    return get_grammar_section_id(lesson.unit, lesson.level, lesson.topic, lesson.title_ru)


async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_value: int) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        lesson = get_lesson_by_callback_value(db, lesson_value)
        if not lesson:
            await query.edit_message_text("Урок не найден.", reply_markup=back_to_menu_keyboard())
            return

        mark_lesson_seen(db, user.id, lesson)
        db.commit()
        context.user_data["grammar_level"] = lesson.level
        context.user_data["grammar_section_id"] = lesson_section_id(lesson)
        context.user_data["grammar_lesson_unit"] = lesson.unit
        context.user_data["grammar_question_index"] = 0
        text = format_lesson_text(lesson)
        reply_markup = grammar_lesson_keyboard(lesson.unit)

    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_value: int, question_index: int) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        lesson = get_lesson_by_callback_value(db, lesson_value)
        if not lesson:
            await query.edit_message_text("Урок не найден.", reply_markup=back_to_menu_keyboard())
            return

        questions = get_lesson_questions(lesson)
        if not questions:
            await query.edit_message_text(
                "В этом уроке пока нет вопросов.",
                reply_markup=grammar_lesson_keyboard(lesson.unit),
            )
            return

        if question_index >= len(questions):
            progress = get_lesson_progress(db, user.id, lesson.unit)
            percent = lesson_progress_percent(progress, lesson)
            await query.edit_message_text(
                f"✅ Тест завершён.\n\nПрохождение урока: {percent}%",
                reply_markup=grammar_lesson_keyboard(lesson.unit),
            )
            return

        mark_lesson_seen(db, user.id, lesson)
        db.commit()
        text, options, _question = format_question_text(lesson, question_index)
        context.user_data["grammar_level"] = lesson.level
        context.user_data["grammar_section_id"] = lesson_section_id(lesson)
        context.user_data["grammar_lesson_unit"] = lesson.unit
        context.user_data["grammar_question_index"] = question_index
        reply_markup = grammar_question_keyboard(lesson.unit, question_index, options)

    await query.edit_message_text(text, reply_markup=reply_markup)


async def grammar_random_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_grammar_levels(update, context)


async def grammar_topics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_grammar_levels(update, context)


async def grammar_levels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    await show_grammar_levels(update, context)


async def grammar_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    level = query.data.split(":", maxsplit=1)[1]
    await show_grammar_sections(update, context, level)


async def grammar_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    _prefix, level, section_id = query.data.split(":", maxsplit=2)
    await show_section_lessons(update, context, level, section_id)


async def grammar_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    lesson_units = context.user_data.get("grammar_lesson_units") or []
    topic_index = int(query.data.split(":", maxsplit=1)[1])
    if topic_index < 0 or topic_index >= len(lesson_units):
        await show_current_lessons_or_levels(update, context)
        return
    await show_lesson(update, context, int(lesson_units[topic_index]))


async def grammar_lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    lesson_value = int(query.data.split(":", maxsplit=1)[1])
    await show_lesson(update, context, lesson_value)


async def grammar_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    lesson_value = int(query.data.split(":", maxsplit=1)[1])
    await show_question(update, context, lesson_value, 0)


async def grammar_next_lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    lesson_value = int(query.data.split(":", maxsplit=1)[1])
    with SessionLocal() as db:
        lesson = get_lesson_by_callback_value(db, lesson_value)
        next_lesson = get_next_lesson(db, lesson) if lesson else None

    if not next_lesson:
        await show_current_lessons_or_levels(update, context)
        return
    await show_lesson(update, context, next_lesson.unit)


async def grammar_next_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    lesson_unit = context.user_data.get("grammar_lesson_unit")
    question_index = context.user_data.get("grammar_question_index", 0)
    if not lesson_unit:
        await show_current_lessons_or_levels(update, context)
        return
    await show_question(update, context, int(lesson_unit), int(question_index) + 1)


async def grammar_lesson_explain_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    lesson_unit = context.user_data.get("grammar_lesson_unit")
    if not lesson_unit:
        await show_current_lessons_or_levels(update, context)
        return
    await show_lesson(update, context, int(lesson_unit))


async def grammar_lessons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    telegram_user = update.effective_user
    if telegram_user:
        with SessionLocal() as db:
            user = get_or_create_user(db, telegram_user)
            if user.level:
                await show_grammar_sections(update, context, user.level)
                return

    await show_current_lessons_or_levels(update, context)


async def grammar_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not query.data or not telegram_user:
        return

    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 4:
        await query.edit_message_text("Формат ответа устарел. Открой урок заново.", reply_markup=back_to_menu_keyboard())
        return

    _prefix, lesson_value_text, question_index_text, selected_index_text = parts
    lesson_value = int(lesson_value_text)
    question_index = int(question_index_text)
    selected_index = int(selected_index_text)

    with SessionLocal() as db:
        user = get_or_create_user(db, telegram_user)
        lesson = get_lesson_by_callback_value(db, lesson_value)
        if not lesson:
            await query.edit_message_text("Урок не найден.", reply_markup=back_to_menu_keyboard())
            return

        questions = get_lesson_questions(lesson)
        if question_index < 0 or question_index >= len(questions):
            await query.edit_message_text("Вопрос не найден.", reply_markup=grammar_lesson_keyboard(lesson.unit))
            return

        question = questions[question_index]
        options = question.get("options") if isinstance(question.get("options"), list) else []
        if selected_index < 0 or selected_index >= len(options):
            await query.edit_message_text("Вариант ответа не найден.", reply_markup=grammar_lesson_keyboard(lesson.unit))
            return

        selected_answer = safe_text(options[selected_index])
        correct_answer = safe_text(question.get("correct_answer"))
        is_correct = selected_answer.lower() == correct_answer.lower()
        save_lesson_answer(db, user.id, lesson, is_correct, question_index)
        add_user_xp(db, user, 5 if is_correct else 1)
        db.commit()

        sentence = solved_sentence(safe_text(question.get("question")), correct_answer)
        if is_correct:
            text = (
                "✅ Верно!\n\n"
                f"{sentence}\n\n"
                f"{safe_text(question.get('explanation_correct'))}\n\n"
                "+5 XP"
            )
        else:
            explanation_wrong = question.get("explanation_wrong") if isinstance(question.get("explanation_wrong"), dict) else {}
            why_wrong = safe_text(explanation_wrong.get(selected_answer)) or safe_text(question.get("explanation_correct"))
            text = (
                "❌ Неверно.\n\n"
                "Правильно:\n"
                f"{correct_answer}\n\n"
                "Почему твой ответ неправильный:\n"
                f"{why_wrong}\n\n"
                "+1 XP"
            )

    context.user_data["grammar_level"] = lesson.level
    context.user_data["grammar_section_id"] = lesson_section_id(lesson)
    context.user_data["grammar_lesson_unit"] = lesson.unit
    context.user_data["grammar_question_index"] = question_index
    await query.edit_message_text(text, reply_markup=grammar_after_answer_keyboard())
