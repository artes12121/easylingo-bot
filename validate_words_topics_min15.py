import json
from pathlib import Path
from collections import Counter

path = Path("data/words_seed.json")
if not path.exists():
    path = Path("words_seed_quality_1_2000_topics_min15.json")

data = json.loads(path.read_text(encoding="utf-8"))

required = ["english", "translation", "transcription", "level", "topic", "part_of_speech", "example_en", "example_ru"]
bad_patterns = [
    "This situation can be",
    "Такая ситуация может быть",
    "This word means",
    "Это называется",
    "Мы называем",
    "we call this",
    "is called:",
    "called:",
]

seen = set()
for i, item in enumerate(data, 1):
    for key in required:
        assert key in item, f"{i}: missing {key}"
        assert str(item[key]).strip(), f"{i}: empty {key}"

    eng = item["english"].lower().strip()
    assert eng not in seen, f"duplicate english: {item['english']}"
    seen.add(eng)

    assert item["level"] in ["A1", "A2", "B1", "B2"], f"{i}: bad level"

    text = item["example_en"] + "\n" + item["example_ru"]
    for bad in bad_patterns:
        assert bad.lower() not in text.lower(), f"{i}: bad example pattern {bad}: {item['english']}"

counts = Counter(item["topic"] for item in data)
small = {topic: count for topic, count in counts.items() if count < 15}
assert not small, f"topics with less than 15 words: {small}"

print(f"OK: {len(data)} words")
print("Topics:")
for topic, count in counts.most_common():
    print(f"- {topic}: {count}")

print("Levels:")
levels = Counter(item["level"] for item in data)
for level, count in sorted(levels.items()):
    print(f"- {level}: {count}")
