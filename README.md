# tg_bot wallet backend

Реализован backend-каркас для PostgreSQL с Alembic, транзакционным учётом ставок/выигрышей, аудитом и anti-fraud правилами.

## Что сделано
- PostgreSQL как целевая БД (`settings.database_url`).
- Alembic миграция `0001_wallet_ledger_audit`.
- Транзакционная обработка `/spin`:
  - `SELECT ... FOR UPDATE` блокирует кошелёк пользователя.
  - уникальные ключи (`external_id`, `idempotency_key`, `uq_round_tx_type`) исключают двойное списание.
- Типы транзакций:
  - `BET_DEBIT`
  - `SPIN_WIN_CREDIT`
  - `DAILY_BONUS_CREDIT`
  - `MISSION_REWARD_CREDIT`
  - `CASHBACK_CREDIT`
- Аудит:
  - неизменяемый журнал `audit_logs` c hash-chain.
  - админский экспорт спорных раундов `/admin/disputed-rounds`.
- Лимиты и фрод-правила:
  - rate limit на `/spin` по количеству раундов в минуту.
  - max bet по уровню пользователя.

## Запуск
```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```
