# Telegram-бот для изучения английского

Каркас проекта для Telegram-бота на Python 3.11+, `python-telegram-bot`, SQLAlchemy 2.0 и SQLite.

## Запуск

1. Перейдите в папку проекта:

```bash
cd language_bot
```

2. Создайте виртуальное окружение:

```bash
python3.11 -m venv .venv
```

3. Активируйте окружение:

```bash
source .venv/bin/activate
```

4. Установите зависимости:

```bash
pip install -r requirements.txt
```

5. Скопируйте пример настроек:

```bash
cp .env.example .env
```

6. Вставьте токен Telegram-бота и другие переменные в `.env`:

```env
BOT_TOKEN=your_real_telegram_bot_token
YANDEX_TRANSLATE_API_KEY=your_yandex_translate_api_key
YANDEX_FOLDER_ID=your_yandex_folder_id
```

Полный список переменных — в `.env.example`.

7. Создайте таблицы и загрузите стартовые данные:

```bash
python seed_data.py
```

8. Запустите бота:

```bash
python bot.py
```

Если `BOT_TOKEN` не указан, запуск завершится сообщением:

```text
BOT_TOKEN не найден. Укажи BOT_TOKEN в .env
```

## Если бот падает с `telegram.error.TimedOut`

1. Проверь интернет и доступ к Telegram API:

```bash
curl -I https://api.telegram.org
```

2. Если запрос зависает или не открывается — включи VPN или укажи прокси в `.env`:

```env
TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
```

3. Обнови код бота и проверь подключение:

```bash
git pull
python check_telegram.py
python bot.py
```

Бот теперь использует увеличенные таймауты и автоматически переподключается при старте.

## Структура

```text
language_bot/
├── bot.py
├── config.py
├── database.py
├── models.py
├── keyboards.py
├── seed_data.py
├── requirements.txt
├── .env.example
├── README.md
├── handlers/
├── services/
└── data/
```
