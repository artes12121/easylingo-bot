from __future__ import annotations

from typing import Optional

from models import Word


EMPTY_TRANSCRIPTIONS = {"", "-", "—"}


def clean_text(value: object) -> str:
    return str(value or "").strip()


def get_word_translation(word: Word) -> str:
    return (
        clean_text(getattr(word, "translation_ru", None))
        or clean_text(getattr(word, "translation", None))
        or clean_text(word.russian)
    )


def format_transcription_value(transcription: Optional[str]) -> str:
    clean_value = clean_text(transcription)
    if clean_value in EMPTY_TRANSCRIPTIONS:
        return ""
    clean_value = clean_value.strip("/")
    if clean_value in EMPTY_TRANSCRIPTIONS:
        return ""
    return f"/{clean_value}/"


def format_transcription_line(word: Word) -> str:
    transcription = format_transcription_value(word.transcription)
    return f"🔤 {transcription}" if transcription else ""


def format_example_block(word: Word) -> str:
    example_en = clean_text(word.example_en)
    example_ru = clean_text(word.example_ru)
    if not example_en or not example_ru:
        return ""
    return f"Пример:\nEN: {example_en}\nRU: {example_ru}"


def format_word_card(word: Word, header: str = "") -> str:
    lines = []
    if header:
        lines.extend([header, ""])

    lines.append(f"🇬🇧 {word.english}")

    transcription_line = format_transcription_line(word)
    if transcription_line:
        lines.append(transcription_line)

    lines.extend(
        [
            f"🇷🇺 {get_word_translation(word)}",
            f"📌 Тема: {clean_text(word.topic) or 'general'}",
            f"📘 Часть речи: {clean_text(word.part_of_speech) or 'word'}",
        ]
    )

    example_block = format_example_block(word)
    if example_block:
        lines.extend(["", example_block])

    return "\n".join(lines)


def format_word_question(word: Word, header: str = "") -> str:
    lines = []
    if header:
        lines.extend([header, ""])

    lines.append(f"🇬🇧 {word.english}")
    transcription_line = format_transcription_line(word)
    if transcription_line:
        lines.append(transcription_line)

    lines.extend(["", "Напиши перевод:"])
    return "\n".join(lines)
