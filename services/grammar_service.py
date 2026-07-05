import json
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import GrammarLesson, GrammarProgress

UNIT_RANGES_BY_LEVEL = {
    "A1": (1, 114),
    "A2": (1, 114),
    "B1": (201, 345),
    "B2": (201, 345),
}

GRAMMAR_LEVELS = [
    ("A1", "🟢 A1"),
    ("A2", "🔵 A2"),
    ("B1", "🟣 B1"),
    ("B2", "🔴 B2"),
]

A1_A2_SECTIONS = [
    ("tenses", "⏱ Основные времена"),
    ("perfect", "⏱ Present Perfect"),
    ("passive", "🔁 Passive / be / have / do"),
    ("modals", "🧱 Modals / future"),
    ("questions", "❓ Вопросы и отрицания"),
    ("verb_patterns", "🧩 Verb patterns"),
    ("pronouns", "👤 Pronouns / possessives"),
    ("articles_nouns", "🔤 Articles / nouns"),
    ("determiners", "👤 Determiners / quantity"),
    ("comparison", "⚖️ Adjectives / adverbs / comparison"),
    ("prepositions", "📍 Prepositions / clauses / linking"),
    ("other", "🧩 Другое"),
]

B1_B2_SECTIONS = [
    ("tenses", "⏱ Tenses"),
    ("modals", "🧱 Modals / conditionals"),
    ("passive", "🔁 Passive"),
    ("reported", "🗣 Reported speech / questions"),
    ("verb_patterns", "🧩 Verb patterns / clauses"),
    ("articles_nouns", "🔤 Nouns / articles / determiners"),
    ("relative", "🔗 Relative clauses / comparison"),
    ("linking", "🔗 Word order / adverbs / linking"),
    ("prepositions", "📍 Prepositions"),
    ("phrasal", "🧨 Phrasal verbs"),
    ("other", "🧩 Другое"),
]

def json_list(value: str) -> list:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def get_lessons_by_level(db: Session, level: str) -> List[GrammarLesson]:
    statement = select(GrammarLesson).where(GrammarLesson.level == level)
    unit_range = UNIT_RANGES_BY_LEVEL.get(level)
    if unit_range:
        statement = statement.where(GrammarLesson.unit >= unit_range[0], GrammarLesson.unit <= unit_range[1])
    statement = statement.order_by(GrammarLesson.unit.asc())
    return list(db.scalars(statement))


def get_grammar_section(unit: int, level: str, topic: str, title_ru: str) -> str:
    section_id = get_grammar_section_id(unit, level, topic, title_ru)
    return get_grammar_section_label(level, section_id)


def get_grammar_section_id(unit: int, level: str, topic: str = "", title_ru: str = "") -> str:
    if 1 <= unit <= 14:
        return "tenses"
    if 15 <= unit <= 20:
        return "perfect"
    if 21 <= unit <= 24:
        return "passive"
    if 25 <= unit <= 35:
        return "modals"
    if 36 <= unit <= 49:
        return "questions"
    if 50 <= unit <= 57:
        return "verb_patterns"
    if 58 <= unit <= 63:
        return "pronouns"
    if 64 <= unit <= 72:
        return "articles_nouns"
    if 73 <= unit <= 83:
        return "determiners"
    if 84 <= unit <= 90:
        return "comparison"
    if 91 <= unit <= 114:
        return "prepositions"

    if 201 <= unit <= 224:
        return "tenses"
    if 225 <= unit <= 241:
        return "modals"
    if 242 <= unit <= 246:
        return "passive"
    if 247 <= unit <= 252:
        return "reported"
    if 253 <= unit <= 268:
        return "verb_patterns"
    if 269 <= unit <= 290:
        return "articles_nouns"
    if 291 <= unit <= 306:
        return "relative"
    if 307 <= unit <= 316:
        return "linking"
    if 317 <= unit <= 331:
        return "prepositions"
    if 332 <= unit <= 345:
        return "phrasal"
    return "other"


def get_grammar_section_label(level: str, section_id: str) -> str:
    sections = dict(get_grammar_section_definitions(level))
    return sections.get(section_id, "🧩 Другое")


def get_grammar_section_definitions(level: str) -> list[tuple[str, str]]:
    if level in {"B1", "B2"}:
        return B1_B2_SECTIONS
    return A1_A2_SECTIONS


def get_grammar_sections_for_level(db: Session, level: str) -> list[tuple[str, str]]:
    lessons = get_lessons_by_level(db, level)
    available_section_ids = {
        get_grammar_section_id(lesson.unit, lesson.level, lesson.topic, lesson.title_ru)
        for lesson in lessons
    }
    return [
        (section_id, label)
        for section_id, label in get_grammar_section_definitions(level)
        if section_id in available_section_ids
    ]


def get_lessons_by_section(db: Session, level: str, section_id: str) -> List[GrammarLesson]:
    return [
        lesson
        for lesson in get_lessons_by_level(db, level)
        if get_grammar_section_id(lesson.unit, lesson.level, lesson.topic, lesson.title_ru) == section_id
    ]


def get_lesson_by_unit_number(db: Session, unit: int) -> Optional[GrammarLesson]:
    return db.scalar(select(GrammarLesson).where(GrammarLesson.unit == unit))


def get_lesson_by_callback_value(db: Session, value: int) -> Optional[GrammarLesson]:
    return get_lesson_by_unit_number(db, value) or get_lesson_by_id(db, value)


def get_lesson_by_id(db: Session, lesson_id: int) -> Optional[GrammarLesson]:
    return db.get(GrammarLesson, lesson_id)


def get_lesson_by_unit(db: Session, level: str, unit: int) -> Optional[GrammarLesson]:
    statement = select(GrammarLesson).where(GrammarLesson.level == level, GrammarLesson.unit == unit)
    return db.scalar(statement)


def get_next_lesson(db: Session, lesson: GrammarLesson) -> Optional[GrammarLesson]:
    statement = (
        select(GrammarLesson)
        .where(GrammarLesson.level == lesson.level, GrammarLesson.unit > lesson.unit)
        .order_by(GrammarLesson.unit.asc())
        .limit(1)
    )
    return db.scalar(statement)


def get_lesson_questions(lesson: GrammarLesson) -> list[dict]:
    return [item for item in json_list(lesson.questions) if isinstance(item, dict)]


def get_lesson_examples(lesson: GrammarLesson) -> list[dict]:
    return [item for item in json_list(lesson.examples) if isinstance(item, dict)]


def get_lesson_common_mistakes(lesson: GrammarLesson) -> list[dict]:
    return [item for item in json_list(lesson.common_mistakes) if isinstance(item, dict)]


def get_or_create_progress(db: Session, user_id: int, unit: int) -> GrammarProgress:
    progress = db.scalar(select(GrammarProgress).where(GrammarProgress.user_id == user_id, GrammarProgress.unit == unit))
    if progress:
        progress.last_seen_at = datetime.utcnow()
        return progress

    progress = GrammarProgress(
        user_id=user_id,
        unit=unit,
        correct_count=0,
        wrong_count=0,
        completed=False,
        last_seen_at=datetime.utcnow(),
    )
    db.add(progress)
    db.flush()
    return progress


def mark_lesson_seen(db: Session, user_id: int, lesson: GrammarLesson) -> GrammarProgress:
    return get_or_create_progress(db, user_id, lesson.unit)


def save_lesson_answer(
    db: Session,
    user_id: int,
    lesson: GrammarLesson,
    is_correct: bool,
    question_index: int,
) -> GrammarProgress:
    progress = get_or_create_progress(db, user_id, lesson.unit)
    if is_correct:
        progress.correct_count += 1
    else:
        progress.wrong_count += 1

    questions_count = len(get_lesson_questions(lesson))
    if questions_count and question_index >= questions_count - 1:
        progress.completed = True
    progress.last_seen_at = datetime.utcnow()
    return progress


def lesson_progress_percent(progress: Optional[GrammarProgress], lesson: GrammarLesson) -> int:
    questions_count = len(get_lesson_questions(lesson))
    if not progress or questions_count == 0:
        return 0
    answered = min(progress.correct_count + progress.wrong_count, questions_count)
    return int(round(answered / questions_count * 100))


def get_lesson_progress(db: Session, user_id: int, unit: int) -> Optional[GrammarProgress]:
    return db.scalar(select(GrammarProgress).where(GrammarProgress.user_id == user_id, GrammarProgress.unit == unit))


def get_grammar_stats(db: Session, user_id: int) -> Dict[str, int]:
    total_lessons_opened = (
        db.scalar(select(func.count()).select_from(GrammarProgress).where(GrammarProgress.user_id == user_id))
        or 0
    )
    completed_lessons = (
        db.scalar(
            select(func.count())
            .select_from(GrammarProgress)
            .where(GrammarProgress.user_id == user_id, GrammarProgress.completed.is_(True))
        )
        or 0
    )
    correct = (
        db.scalar(
            select(func.coalesce(func.sum(GrammarProgress.correct_count), 0)).where(GrammarProgress.user_id == user_id)
        )
        or 0
    )
    wrong = (
        db.scalar(
            select(func.coalesce(func.sum(GrammarProgress.wrong_count), 0)).where(GrammarProgress.user_id == user_id)
        )
        or 0
    )
    return {
        "total": int(total_lessons_opened),
        "completed": int(completed_lessons),
        "correct": int(correct),
        "wrong": int(wrong),
    }


def count_grammar_tasks(db: Session, level: Optional[str] = None) -> int:
    statement = select(func.count()).select_from(GrammarLesson)
    if level:
        statement = statement.where(GrammarLesson.level == level)
    return db.scalar(statement) or 0


def get_topics_by_level(db: Session, level: str) -> List[str]:
    return [lesson.topic for lesson in get_lessons_by_level(db, level)]
