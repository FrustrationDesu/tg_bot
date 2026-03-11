# tg_bot

Telegram-бот на **aiogram** с командами слотов и системы наград.

## Возможности

- Базовые команды:
  - `/start` — приветствие и подсказка по командам.
  - `/balance` — текущий баланс пользователя.
  - `/spin <amount>` — спин со ставкой и расчетом выплаты.
- Награды и прогресс:
  - `/rewards` — сводка по балансу, стрику, VIP и антиабуз-флагу.
  - `/daily` — ежедневный бонус.
  - `/missions` — прогресс миссий и клейм наград.
  - `/vip` — текущий VIP-уровень и оборот.
- Валидация ставок:
  - только целое число;
  - между `MIN_BET` и `MAX_BET`;
  - не больше текущего баланса.
- Поддержка запуска через **polling** (по умолчанию) и **webhook**.

## Стек

- Основной рантайм бота: **aiogram**.
- HTTP-сервер для webhook: **aiohttp**.
- Конфигурация: **python-dotenv**.
- Хранилище наград/VIP/миссий: SQLite (через `bot/db/schema.sql`).

## Локальный запуск (polling)

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Подготовьте `.env`:

```bash
cp .env.example .env
```

4. Заполните минимум:

- `BOT_TOKEN`
- `DB_URL` (например, `sqlite+aiosqlite:///./bot.db`)
- `MIN_BET`
- `MAX_BET`

5. Запустите бота:

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
