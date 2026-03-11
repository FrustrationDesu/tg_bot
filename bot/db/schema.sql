PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vip_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    min_turnover REAL NOT NULL,
    cashback_rate REAL NOT NULL DEFAULT 0,
    daily_bonus_multiplier REAL NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    wallet_balance REAL NOT NULL DEFAULT 0,
    total_bet_turnover REAL NOT NULL DEFAULT 0,
    total_net_loss REAL NOT NULL DEFAULT 0,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_daily_claim_at TEXT,
    daily_cooldown_until TEXT,
    vip_tier_id INTEGER,
    device_fingerprint TEXT,
    last_ip TEXT,
    is_flagged_multiaccount INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vip_tier_id) REFERENCES vip_tiers(id)
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    tx_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    reference_type TEXT,
    reference_id TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS daily_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    claim_date TEXT NOT NULL,
    streak_day INTEGER NOT NULL,
    reward_amount REAL NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, claim_date)
);

CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    objective_type TEXT NOT NULL,
    objective_target INTEGER NOT NULL,
    reward_amount REAL NOT NULL,
    cooldown_hours INTEGER NOT NULL DEFAULT 24,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mission_id INTEGER NOT NULL,
    period_date TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    reward_claimed_at TEXT,
    reward_tx_id INTEGER,
    idempotency_key TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (mission_id) REFERENCES missions(id),
    FOREIGN KEY (reward_tx_id) REFERENCES wallet_transactions(id),
    UNIQUE(user_id, mission_id, period_date)
);

CREATE TABLE IF NOT EXISTS cashback_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    net_loss REAL NOT NULL,
    cashback_rate REAL NOT NULL,
    cashback_amount REAL NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_users_device_fp ON users(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_users_last_ip ON users(last_ip);
CREATE INDEX IF NOT EXISTS idx_wallet_user_created ON wallet_transactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_daily_rewards_user_date ON daily_rewards(user_id, claim_date);
CREATE INDEX IF NOT EXISTS idx_user_missions_user_period ON user_missions(user_id, period_date);
