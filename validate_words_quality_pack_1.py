import json
from pathlib import Path

path = Path("data/words_seed.json")
if not path.exists():
    path = Path("words_seed_quality_pack_1_200.json")

data = json.loads(path.read_text(encoding="utf-8"))

required = ["english", "translation", "transcription", "level", "topic", "part_of_speech", "example_en", "example_ru"]
bad_patterns = [
    "This situation can be",
    "Такая ситуация может быть",
    "This is",
    "It is",
    "This word means",
    "Это называется",
    "Мы называем",
    "called",
    "is called",
]

seen = set()
for i, item in enumerate(data, 1):
    for key in required:
        assert key in item, f"{i}: missing {key}"
        assert str(item[key]).strip(), f"{i}: empty {key}"
    eng = item["english"]
    assert eng not in seen, f"duplicate english: {eng}"
    seen.add(eng)
    assert item["level"] in ["A1", "A2", "B1", "B2"], f"{i}: bad level"
    assert item["translation"] == item.get("translation_ru", item["translation"]), f"{i}: translation mismatch"
    text = item["example_en"] + "\n" + item["example_ru"]
    for bad in bad_patterns:
        assert bad.lower() not in text.lower(), f"{i}: bad example pattern {bad}: {eng}"
print(f"OK: {len(data)} words")
topics = {}
for item in data:
    topics[item["topic"]] = topics.get(item["topic"], 0) + 1
print("Topics:")
for topic, count in sorted(topics.items()):
    print(f"- {topic}: {count}")
