from __future__ import annotations

import re

from config import YANDEX_FOLDER_ID, YANDEX_TRANSLATE_API_KEY


YANDEX_TRANSLATE_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"


class TranslatorConfigError(Exception):
    pass


class TranslatorAuthError(Exception):
    pass


class TranslatorRateLimitError(Exception):
    pass


class TranslatorAPIError(Exception):
    pass


def is_translator_configured() -> bool:
    return bool(YANDEX_TRANSLATE_API_KEY and YANDEX_FOLDER_ID)


def has_russian_letters(text: str) -> bool:
    return bool(re.search(r"[а-яёА-ЯЁ]", text))


def detect_direction(text: str, mode: str) -> tuple[str, str]:
    if mode == "en_ru":
        return "en", "ru"
    if mode == "ru_en":
        return "ru", "en"
    if has_russian_letters(text):
        return "ru", "en"
    return "en", "ru"


def format_direction(source_lang: str, target_lang: str) -> str:
    return f"{source_lang.upper()} → {target_lang.upper()}"


def format_mode(mode: str) -> str:
    if mode == "en_ru":
        return "EN → RU"
    if mode == "ru_en":
        return "RU → EN"
    return "Авто"


def is_single_word(text: str) -> bool:
    return len(text.strip().split()) == 1


def build_hint(text: str) -> str:
    if len(text) > 120:
        return ""
    if is_single_word(text):
        return "Для отдельных слов перевод может зависеть от контекста."
    return "Если нужен не дословный перевод, отправь фразу целиком, а не отдельные слова."


def format_translation_response(translated_text: str, source_lang: str, target_lang: str, mode: str, source_text: str) -> str:
    parts = [
        "🌍 Перевод:",
        translated_text,
        "",
        "🧠 Разбор:",
        f"Направление: {format_direction(source_lang, target_lang)}",
        f"Режим: {format_mode(mode)}",
    ]

    hint = build_hint(source_text)
    if hint:
        parts.extend(["", "💬 Подсказка:", hint])

    return "\n".join(parts)


async def translate_text(text: str, mode: str = "auto") -> str:
    if not is_translator_configured():
        raise TranslatorConfigError("Yandex Translate is not configured")

    try:
        import aiohttp
    except ImportError as error:
        raise TranslatorAPIError("aiohttp is not installed") from error

    source_lang, target_lang = detect_direction(text, mode)
    headers = {
        "Authorization": f"Api-Key {YANDEX_TRANSLATE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "folderId": YANDEX_FOLDER_ID,
        "texts": [text],
        "targetLanguageCode": target_lang,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(YANDEX_TRANSLATE_URL, headers=headers, json=payload) as response:
            response_text = await response.text()

            if response.status in {401, 403}:
                raise TranslatorAuthError(response_text)
            if response.status == 429:
                raise TranslatorRateLimitError(response_text)
            if response.status >= 400:
                raise TranslatorAPIError(f"{response.status}: {response_text}")

            data = await response.json()

    translations = data.get("translations") or []
    translated_text = ""
    if translations and isinstance(translations[0], dict):
        translated_text = str(translations[0].get("text") or "").strip()

    if not translated_text:
        raise TranslatorAPIError("Empty translation response")

    return format_translation_response(translated_text, source_lang, target_lang, mode, text)
