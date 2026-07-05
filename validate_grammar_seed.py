import json
from pathlib import Path

path = Path("data/grammar_seed.json")
if not path.exists():
    path = Path("grammar_seed_essential_units_1_30.json")

data = json.loads(path.read_text(encoding="utf-8"))
required_lesson = ["unit","level","topic","title_ru","explanation_ru","formula","examples","common_mistakes","questions"]
required_question = ["type","question","options","correct_answer","explanation_correct","explanation_wrong"]

assert isinstance(data, list), "Root must be a list"
units = set()
total_questions = 0

for i, lesson in enumerate(data, 1):
    for key in required_lesson:
        assert key in lesson, f"Lesson {i}: missing {key}"
    assert lesson["unit"] not in units, f"Duplicate unit {lesson['unit']}"
    units.add(lesson["unit"])
    assert lesson["level"] in ["A1","A2","B1","B2"], f"Lesson {i}: bad level"
    assert isinstance(lesson["examples"], list) and lesson["examples"], f"Lesson {i}: examples empty"
    assert isinstance(lesson["common_mistakes"], list) and lesson["common_mistakes"], f"Lesson {i}: common_mistakes empty"
    assert isinstance(lesson["questions"], list) and lesson["questions"], f"Lesson {i}: questions empty"
    for j, question in enumerate(lesson["questions"], 1):
        for key in required_question:
            assert key in question, f"Lesson {i} question {j}: missing {key}"
        assert question["correct_answer"] in question["options"], f"Lesson {i} question {j}: correct answer not in options"
        total_questions += 1

print(f"OK: {len(data)} lessons, {total_questions} questions")
print("Units:", min(units), "-", max(units))
