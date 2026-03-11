# tg_bot

Минимальный Telegram-бот (слот-механика) на `aiogram`.

## Возможности

- Команды:
  - `/start` — приветствие и подсказка по командам.
  - `/balance` — текущий баланс пользователя.
  - `/spin <amount>` — спин со ставкой и расчетом выплаты.
- Валидация ставок:
  - только целое число;
  - между `MIN_BET` и `MAX_BET`;
  - не больше текущего баланса.
- Централизованный логгер.
- Поддержка запуска через **polling** (по умолчанию) и **webhook**.

## Структура

```text
bot/
  main.py
  config.py
  logger.py
  handlers/
    commands.py
  services/
    game.py
    validation.py
    wallet.py
```

## Зависимости

### Обязательные

Устанавливаются через `pip install -r requirements.txt`:

- `aiogram` (v3) — основной фреймворк Telegram-бота (`Dispatcher`, `Router`, middleware).
- `aiohttp` — HTTP-сервер для webhook-режима в `bot/main.py`.
- `python-dotenv` — загрузка переменных окружения в `bot/config.py`.
- `aiosqlite` — async-драйвер для `DB_URL=sqlite+aiosqlite:///...`.
- `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `pydantic-settings`.

### Опциональные

- `python-telegram-bot` — нужен только если вы планируете использовать `bot/handlers/rewards.py` через helper `register_rewards_handlers(...)` (интеграция с `telegram.ext.CommandHandler`). В базовый запуск через `aiogram` этот пакет не входит.

## Локальный запуск (polling)

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Подготовьте `.env` на основе примера:

```bash
cp .env.example .env
```

4. Заполните минимум:

- `BOT_TOKEN`
- `DB_URL`
- `MIN_BET`
- `MAX_BET`

5. Запустите:

```bash
python -m bot.main
```

## Прод-запуск (webhook)

Для webhook установите переменные:

- `WEBHOOK_URL` — публичный HTTPS URL, например `https://bot.example.com`
- `WEBHOOK_PATH` — путь webhook, например `/webhook`
- `HOST` и `PORT` — адрес и порт локального HTTP-сервера

Пример запуска:

```bash
WEBHOOK_URL=https://bot.example.com HOST=0.0.0.0 PORT=8080 python -m bot.main
```

Важно: сервер должен быть доступен из интернета по HTTPS.
