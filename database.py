from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()


def ensure_sqlite_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    with engine.begin() as connection:
        if "user_words" in table_names:
            columns = {column["name"] for column in inspector.get_columns("user_words")}
            migrations = {
                "learning_stage": "ALTER TABLE user_words ADD COLUMN learning_stage INTEGER NOT NULL DEFAULT 0",
                "review_streak": "ALTER TABLE user_words ADD COLUMN review_streak INTEGER NOT NULL DEFAULT 0",
                "learning_session_id": "ALTER TABLE user_words ADD COLUMN learning_session_id VARCHAR(255)",
                "is_learning_done": "ALTER TABLE user_words ADD COLUMN is_learning_done BOOLEAN NOT NULL DEFAULT 0",
            }

            for column_name, statement in migrations.items():
                if column_name not in columns:
                    connection.execute(text(statement))

        if "words" in table_names:
            columns = {column["name"] for column in inspector.get_columns("words")}
            migrations = {
                "translation": "ALTER TABLE words ADD COLUMN translation VARCHAR(255)",
                "translation_ru": "ALTER TABLE words ADD COLUMN translation_ru VARCHAR(255)",
            }

            for column_name, statement in migrations.items():
                if column_name not in columns:
                    connection.execute(text(statement))

        if "grammar_lessons" in table_names:
            columns = {column["name"] for column in inspector.get_columns("grammar_lessons")}
            migrations = {
                "source_book": "ALTER TABLE grammar_lessons ADD COLUMN source_book TEXT",
                "source_unit": "ALTER TABLE grammar_lessons ADD COLUMN source_unit INTEGER",
            }

            for column_name, statement in migrations.items():
                if column_name not in columns:
                    connection.execute(text(statement))

        if "translation_history" in table_names:
            columns = {column["name"] for column in inspector.get_columns("translation_history")}
            if "mode" not in columns:
                connection.execute(
                    text("ALTER TABLE translation_history ADD COLUMN mode VARCHAR(64) NOT NULL DEFAULT 'auto'")
                )
                if "direction" in columns:
                    connection.execute(
                        text(
                            "UPDATE translation_history "
                            "SET mode = direction "
                            "WHERE direction IS NOT NULL AND direction != ''"
                        )
                    )
