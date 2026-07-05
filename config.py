from dotenv import load_dotenv
import os


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
YANDEX_TRANSLATE_API_KEY = os.getenv("YANDEX_TRANSLATE_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///language_bot.db")
