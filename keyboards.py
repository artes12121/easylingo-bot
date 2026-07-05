from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("A1", callback_data="level:A1"),
                InlineKeyboardButton("A2", callback_data="level:A2"),
            ],
            [
                InlineKeyboardButton("B1", callback_data="level:B1"),
                InlineKeyboardButton("B2", callback_data="level:B2"),
            ],
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Учить слова", callback_data="learn_words")],
            [InlineKeyboardButton("🧠 Заучивание", callback_data="learning_drill")],
            [InlineKeyboardButton("🔁 Повторение", callback_data="review_words")],
            [InlineKeyboardButton("📝 Грамматика", callback_data="grammar")],
            [InlineKeyboardButton("🌍 Переводчик", callback_data="translator")],
            [InlineKeyboardButton("📊 Прогресс", callback_data="progress")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")]])


def translator_intro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇬🇧 EN → RU", callback_data="translator_mode:en_ru"),
                InlineKeyboardButton("🇷🇺 RU → EN", callback_data="translator_mode:ru_en"),
            ],
            [InlineKeyboardButton("🔄 Автоопределение", callback_data="translator_mode:auto")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="translator_back")],
        ]
    )


def translator_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Перевести ещё", callback_data="translator_again")],
            [
                InlineKeyboardButton("🇬🇧 EN → RU", callback_data="translator_mode:en_ru"),
                InlineKeyboardButton("🇷🇺 RU → EN", callback_data="translator_mode:ru_en"),
            ],
            [InlineKeyboardButton("🔄 Авто", callback_data="translator_mode:auto")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="translator_back")],
        ]
    )


def learn_topics_keyboard(topics: list[str], labels: list[str] = None) -> InlineKeyboardMarkup:
    button_labels = labels or topics
    rows = [
        [InlineKeyboardButton(label, callback_data=f"learn_topic:{index}")]
        for index, label in enumerate(button_labels)
    ]
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def learn_word_keyboard(word_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Знаю", callback_data="word_known"),
                InlineKeyboardButton("❌ Не знаю", callback_data="word_unknown"),
            ],
            [InlineKeyboardButton("➡️ Следующее", callback_data="next_word")],
            [InlineKeyboardButton("⬅️ К темам", callback_data="learn_topics_back")],
        ]
    )


def learn_topic_done_keyboard(show_learning_button: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if show_learning_button:
        rows.append([InlineKeyboardButton("🧠 Перейти в заучивание", callback_data="learning_drill")])
    rows.extend(
        [
            [InlineKeyboardButton("⬅️ К темам", callback_data="learn_topics_back")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def topic_completed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Пройти тему заново", callback_data="repeat_topic")],
            [InlineKeyboardButton("🧠 Заучивание", callback_data="learning_drill")],
            [InlineKeyboardButton("🔁 Повторение", callback_data="review_words")],
            [InlineKeyboardButton("⬅️ К темам", callback_data="learn_topics_back")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def repeat_topic_completed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Пройти ещё раз", callback_data="repeat_topic")],
            [InlineKeyboardButton("🧠 Заучивание", callback_data="learning_drill")],
            [InlineKeyboardButton("🔁 Повторение", callback_data="review_words")],
            [InlineKeyboardButton("⬅️ К темам", callback_data="learn_topics_back")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def learning_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Учить слова", callback_data="learn_words")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def learning_card_keyboard(user_word_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➡️ Следующее", callback_data="learning_next")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def learning_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧠 Следующее из заучивания", callback_data="learning_drill")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def learning_complete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Повторение", callback_data="review_words")],
            [InlineKeyboardButton("📚 Учить новую тему", callback_data="learn_words")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def no_reviews_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Учить слова", callback_data="learn_words")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def review_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➡️ Следующее слово", callback_data="review_words")],
            [InlineKeyboardButton("🧠 Заучивание", callback_data="learning_drill")],
            [InlineKeyboardButton("📚 Учить новые слова", callback_data="learn_words")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Изменить уровень", callback_data="change_level")],
            [InlineKeyboardButton("Сбросить прогресс", callback_data="reset_progress")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def reset_progress_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Да, сбросить", callback_data="confirm_reset_progress")],
            [InlineKeyboardButton("Нет", callback_data="cancel_reset_progress")],
        ]
    )


def grammar_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚 Уроки по моему уровню", callback_data="grammar_lessons")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def grammar_lessons_keyboard(lessons: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{index}. {lesson.title_ru}", callback_data=f"grammar_lesson:{lesson.id}")]
        for index, lesson in enumerate(lessons, start=1)
    ]
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def grammar_lesson_keyboard(lesson_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧪 Пройти тест", callback_data=f"grammar_test:{lesson_id}")],
            [InlineKeyboardButton("➡️ Следующий урок", callback_data=f"grammar_next_lesson:{lesson_id}")],
            [InlineKeyboardButton("⬅️ К урокам", callback_data="grammar_lessons")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def grammar_question_keyboard(lesson_id: int, question_index: int, options: list[str]) -> InlineKeyboardMarkup:
    letters = ["A", "B", "C", "D", "E", "F"]
    rows = [
        [InlineKeyboardButton(f"{letters[index]}) {option}", callback_data=f"grammar_answer:{lesson_id}:{question_index}:{index}")]
        for index, option in enumerate(options)
    ]
    rows.append([InlineKeyboardButton("📘 Объяснение урока", callback_data="grammar_lesson_explain")])
    rows.append([InlineKeyboardButton("⬅️ К урокам", callback_data="grammar_lessons")])
    return InlineKeyboardMarkup(rows)


def grammar_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("A", callback_data=f"grammar_answer:{task_id}:A"),
                InlineKeyboardButton("B", callback_data=f"grammar_answer:{task_id}:B"),
                InlineKeyboardButton("C", callback_data=f"grammar_answer:{task_id}:C"),
                InlineKeyboardButton("D", callback_data=f"grammar_answer:{task_id}:D"),
            ],
            [InlineKeyboardButton("➡️ Другое задание", callback_data="grammar_random")],
            [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
        ]
    )


def grammar_after_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➡️ Следующий вопрос", callback_data="grammar_next_question")],
            [InlineKeyboardButton("📘 Объяснение урока", callback_data="grammar_lesson_explain")],
            [InlineKeyboardButton("⬅️ К урокам", callback_data="grammar_lessons")],
        ]
    )


def grammar_topics_keyboard(topics: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(topic, callback_data=f"grammar_topic:{index}")] for index, topic in enumerate(topics)]
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)
