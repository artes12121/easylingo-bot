from __future__ import annotations


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
