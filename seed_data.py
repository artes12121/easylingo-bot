from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from database import SessionLocal, init_db
from models import GrammarLesson, Word


BASE_DIR = Path(__file__).resolve().parent
WORDS_PATH = BASE_DIR / "data" / "words_seed.json"
WORD_PACKS_DIR = BASE_DIR / "data" / "word_packs"
GRAMMAR_PATH = BASE_DIR / "data" / "grammar_seed.json"
GRAMMAR_PACKS_DIR = BASE_DIR / "data" / "grammar_packs"
GRAMMAR_PACKS_B1B2_DIR = BASE_DIR / "data" / "grammar_packs_b1b2"
GRAMMAR_PACK_DIRS = (GRAMMAR_PACKS_DIR, GRAMMAR_PACKS_B1B2_DIR)


class SeedDataError(Exception):
    pass


def load_json_array(path: Path, required: bool = True) -> list[dict]:
    if not path.exists():
        if required:
            raise SeedDataError(f"Файл {path} не найден.")
        return []

    raw_text = path.read_text(encoding="utf-8")
    if not required and not raw_text.strip():
        return []

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise SeedDataError(f"Файл {path} содержит некорректный JSON: {error}") from error

    if not isinstance(data, list):
        raise SeedDataError(f"Файл {path} должен содержать JSON-массив.")
    return data


def load_grammar_items() -> list[dict]:
    pack_paths = []
    for pack_dir in GRAMMAR_PACK_DIRS:
        if pack_dir.exists() and pack_dir.is_dir():
            pack_paths.extend(path for path in pack_dir.glob("*.json") if path.is_file())
    pack_paths = sorted(pack_paths, key=lambda path: (path.parent.name, path.name))

    if not pack_paths:
        return load_json_array(GRAMMAR_PATH, required=False)

    print("Loading grammar packs:")
    grammar_items: list[dict] = []
    seen_units: set[int] = set()

    for pack_path in pack_paths:
        pack_items = load_json_array(pack_path, required=True)
        pack_label = f"{pack_path.parent.name}/{pack_path.name}"
        print(f"- {pack_label}: {len(pack_items)} lessons")

        for item in pack_items:
            if not isinstance(item, dict):
                continue

            try:
                unit = int(item.get("unit"))
            except (TypeError, ValueError):
                grammar_items.append(item)
                continue

            if unit in seen_units:
                raise SeedDataError(f"Duplicate grammar unit: {unit}")
            seen_units.add(unit)
            grammar_items.append(item)

    print(f"Total grammar lessons loaded: {len(grammar_items)}")
    return grammar_items


def load_word_items() -> list[dict]:
    words = load_json_array(WORDS_PATH, required=True)
    if not WORD_PACKS_DIR.exists():
        return words

    pack_paths = sorted(path for path in WORD_PACKS_DIR.glob("*.json") if path.is_file())
    if not pack_paths:
        return words

    print("Loading word packs:")
    for pack_path in pack_paths:
        pack_items = load_json_array(pack_path, required=True)
        print(f"- {pack_path.name}: {len(pack_items)} words")
        words.extend(pack_items)

    print(f"Total word cards loaded: {len(words)}")
    return words


def seed_words(db) -> tuple[int, int]:
    words = load_word_items()
    existing_words = {
        (word.english.lower(), word.level): word
        for word in db.scalars(select(Word))
    }

    added = 0
    skipped = 0
    required_fields = {"english", "level"}

    for item in words:
        if not isinstance(item, dict) or not required_fields.issubset(item):
            skipped += 1
            continue

        english = clean_seed_text(item.get("english"))
        level = clean_seed_text(item.get("level"))
        legacy_russian = clean_seed_text(item.get("russian"))
        translation = clean_seed_text(item.get("translation")) or clean_seed_text(item.get("translation_ru")) or legacy_russian
        translation_ru = clean_seed_text(item.get("translation_ru")) or translation or legacy_russian
        russian = translation_ru
        if not english or not level or not russian:
            skipped += 1
            continue

        transcription = clean_seed_text(item.get("transcription"))
        part_of_speech = clean_seed_text(item.get("part_of_speech"))
        example_en = clean_seed_text(item.get("example_en"))
        example_ru = clean_seed_text(item.get("example_ru"))
        topic = clean_seed_text(item.get("topic")) or "general"

        key = (english.lower(), level)
        if key in existing_words:
            word = existing_words[key]
            word.translation = translation
            word.translation_ru = translation_ru
            word.russian = russian
            word.transcription = transcription
            word.part_of_speech = part_of_speech
            word.example_en = example_en
            word.example_ru = example_ru
            word.topic = topic
            skipped += 1
            continue

        word = Word(
            english=english,
            translation=translation,
            translation_ru=translation_ru,
            russian=russian,
            transcription=transcription,
            level=level,
            part_of_speech=part_of_speech,
            example_en=example_en,
            example_ru=example_ru,
            topic=topic,
        )
        db.add(
            word
        )
        existing_words[key] = word
        added += 1

    return added, skipped


def clean_seed_text(value) -> str:
    return str(value or "").strip()


def json_text(value) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def normalize_optional_text(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_new_grammar_lesson(item: dict) -> dict | None:
    required_fields = {
        "unit",
        "level",
        "topic",
        "title_ru",
        "explanation_ru",
        "formula",
        "examples",
        "common_mistakes",
        "questions",
    }
    if not required_fields.issubset(item):
        return None

    try:
        unit = int(item["unit"])
    except (TypeError, ValueError):
        return None

    level = str(item["level"]).strip()
    topic = str(item["topic"]).strip()
    title_ru = str(item["title_ru"]).strip()
    explanation_ru = str(item["explanation_ru"]).strip()
    formula = str(item["formula"]).strip()
    questions = item.get("questions") or []

    if not unit or not level or not topic or not title_ru or not explanation_ru or not isinstance(questions, list):
        return None

    return {
        "unit": unit,
        "source_book": normalize_optional_text(item.get("source_book")),
        "source_unit": normalize_optional_int(item.get("source_unit")),
        "level": level,
        "topic": topic,
        "title_ru": title_ru,
        "explanation_ru": explanation_ru,
        "formula": formula,
        "examples": item.get("examples") if isinstance(item.get("examples"), list) else [],
        "common_mistakes": item.get("common_mistakes") if isinstance(item.get("common_mistakes"), list) else [],
        "questions": questions,
    }


def legacy_items_to_lessons(grammar_items: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    required_fields = {
        "level",
        "topic",
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "explanation",
    }

    for item in grammar_items:
        if not isinstance(item, dict) or not required_fields.issubset(item):
            continue
        level = str(item["level"]).strip()
        topic = str(item["topic"]).strip()
        if level and topic:
            grouped[(level, topic)].append(item)

    lessons = []
    for unit, ((level, topic), items) in enumerate(sorted(grouped.items()), start=1):
        questions = []
        for item in items:
            options = [
                str(item["option_a"]).strip(),
                str(item["option_b"]).strip(),
                str(item["option_c"]).strip(),
                str(item["option_d"]).strip(),
            ]
            correct_option = str(item["correct_option"]).strip().upper()
            option_index = {"A": 0, "B": 1, "C": 2, "D": 3}.get(correct_option)
            if option_index is None:
                continue
            correct_answer = options[option_index]
            questions.append(
                {
                    "type": "multiple_choice",
                    "question": str(item["question"]).strip(),
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation_correct": str(item["explanation"]).strip(),
                    "explanation_wrong": {},
                }
            )

        if questions:
            lessons.append(
                {
                    "unit": unit,
                    "source_book": None,
                    "source_unit": None,
                    "level": level,
                    "topic": topic,
                    "title_ru": topic,
                    "explanation_ru": questions[0]["explanation_correct"],
                    "formula": "",
                    "examples": [],
                    "common_mistakes": [],
                    "questions": questions,
                }
            )

    return lessons


def seed_grammar(db) -> tuple[int, int]:
    grammar_items = load_grammar_items()
    added = 0
    updated = 0

    lessons = []
    for item in grammar_items:
        if isinstance(item, dict):
            lesson = normalize_new_grammar_lesson(item)
            if lesson:
                lessons.append(lesson)

    if not lessons:
        lessons = legacy_items_to_lessons(grammar_items)

    for lesson in lessons:
        existing = db.scalar(select(GrammarLesson).where(GrammarLesson.unit == lesson["unit"]))
        if existing:
            existing.source_book = lesson["source_book"]
            existing.source_unit = lesson["source_unit"]
            existing.level = lesson["level"]
            existing.topic = lesson["topic"]
            existing.title_ru = lesson["title_ru"]
            existing.explanation_ru = lesson["explanation_ru"]
            existing.formula = lesson["formula"]
            existing.examples = json_text(lesson["examples"])
            existing.common_mistakes = json_text(lesson["common_mistakes"])
            existing.questions = json_text(lesson["questions"])
            updated += 1
            continue

        db.add(
            GrammarLesson(
                unit=lesson["unit"],
                source_book=lesson["source_book"],
                source_unit=lesson["source_unit"],
                level=lesson["level"],
                topic=lesson["topic"],
                title_ru=lesson["title_ru"],
                explanation_ru=lesson["explanation_ru"],
                formula=lesson["formula"],
                examples=json_text(lesson["examples"]),
                common_mistakes=json_text(lesson["common_mistakes"]),
                questions=json_text(lesson["questions"]),
            )
        )
        added += 1

    return added, updated


def main() -> int:
    try:
        init_db()
        with SessionLocal() as db:
            words_added, words_skipped = seed_words(db)
            grammar_added, grammar_updated = seed_grammar(db)
            db.commit()

        print(f"Слов добавлено: {words_added}")
        print(f"Слов пропущено как дубликаты: {words_skipped}")
        print(f"Грамматических уроков добавлено: {grammar_added}")
        print(f"Грамматических уроков обновлено: {grammar_updated}")
        return 0
    except SeedDataError as error:
        print(f"Ошибка seed_data: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
