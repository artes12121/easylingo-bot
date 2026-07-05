import json
import sys
from pathlib import Path
from collections import Counter

path = Path("data/words_seed.json")
if not path.exists():
    path = Path("words_seed_2000.json")

required = ["english","translation","translation_ru","transcription","level","part_of_speech","example_en","example_ru","topic"]
levels = {"A1","A2","B1","B2"}
pos = {"noun","verb","adjective","adverb","pronoun","preposition","conjunction","phrase","modal verb","determiner","number"}
bad_patterns = [
    "The English word",
    "This word",
    "I see the",
    "have the letter",
    "this situation can be",
    "такая ситуация может быть",
    "this word means",
    "это называется",
    "мы называем",
    "is called",
]

errors = []
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as e:
    print("JSON error:", e)
    sys.exit(1)

if not isinstance(data, list):
    print("Файл должен быть JSON-массивом.")
    sys.exit(1)

seen = set()
empty_transcription = 0

for i, item in enumerate(data):
    if not isinstance(item, dict):
        errors.append(f"{i}: item is not object")
        continue
    for f in required:
        if f not in item:
            errors.append(f"{i}: missing {f}")
        elif f not in {"transcription", "example_en", "example_ru"} and str(item.get(f, "")).strip() == "":
            errors.append(f"{i}: empty {f}")
    if str(item.get("transcription", "")).strip() == "":
        empty_transcription += 1
    if item.get("level") not in levels:
        errors.append(f"{i}: bad level {item.get('level')}")
    if item.get("part_of_speech") not in pos:
        errors.append(f"{i}: bad part_of_speech {item.get('part_of_speech')}")
    key = (str(item.get("english","")).lower(), item.get("level"))
    if key in seen:
        errors.append(f"{i}: duplicate english+level {key}")
    seen.add(key)

    en_ex = str(item.get("example_en",""))
    ru_ex = str(item.get("example_ru",""))
    for pat in bad_patterns:
        if pat.lower() in en_ex.lower() or pat.lower() in ru_ex.lower():
            errors.append(f"{i}: bad pattern {pat}: {item.get('english')}")
    if "means" in en_ex.lower() and "English word" in en_ex:
        errors.append(f"{i}: bad means-template: {item.get('english')}")
    if "означает" in ru_ex.lower() and "английское слово" in ru_ex.lower():
        errors.append(f"{i}: bad ru means-template: {item.get('english')}")

counts = Counter(item.get("level") for item in data if isinstance(item, dict))
topics = Counter(item.get("topic") for item in data if isinstance(item, dict))

print(f"Всего карточек: {len(data)}")
print("По уровням:")
for lvl in ["A1","A2","B1","B2"]:
    print(f"- {lvl}: {counts[lvl]}")
print(f"Пустых транскрипций: {empty_transcription}")
print("\nТоп тем:")
for topic, count in topics.most_common(30):
    print(f"- {topic}: {count}")

if errors:
    print("\nОшибки:")
    for e in errors[:50]:
        print("-", e)
    sys.exit(1)

print("\nПроблем не найдено.")
