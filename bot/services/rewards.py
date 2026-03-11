from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class RewardLimits:
    max_daily_reward: float = 100.0
    max_mission_reward_per_day: float = 500.0
    max_cashback_per_period: float = 1000.0


class RewardsService:
    """Service for rewards, VIP, missions and cashback backed by a unified ledger."""

    def __init__(self, db_path: str, limits: RewardLimits | None = None) -> None:
        self.db_path = db_path
        self.limits = limits or RewardLimits()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _as_iso(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).isoformat()

    def ensure_schema(self, schema_sql: str) -> None:
        with self._connect() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    def ensure_default_vip_tiers(self) -> None:
        tiers = [
            ("Bronze", 0, 0.02, 1.0),
            ("Silver", 1_000, 0.04, 1.15),
            ("Gold", 10_000, 0.07, 1.35),
            ("Platinum", 50_000, 0.1, 1.6),
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO vip_tiers(name, min_turnover, cashback_rate, daily_bonus_multiplier)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    min_turnover = excluded.min_turnover,
                    cashback_rate = excluded.cashback_rate,
                    daily_bonus_multiplier = excluded.daily_bonus_multiplier
                """,
                tiers,
            )
            conn.commit()

    def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        device_fingerprint: str | None = None,
        ip: str | None = None,
    ) -> sqlite3.Row:
        now = self._as_iso(self._now())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users(telegram_id, username, device_fingerprint, last_ip, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    device_fingerprint = COALESCE(excluded.device_fingerprint, users.device_fingerprint),
                    last_ip = COALESCE(excluded.last_ip, users.last_ip),
                    updated_at = excluded.updated_at
                """,
                (telegram_id, username, device_fingerprint, ip, now),
            )
            user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            conn.commit()
            return user

    def run_multiaccount_heuristics(self, user_id: int, same_signal_limit: int = 3) -> bool:
        """Flag users sharing IP/device with many accounts as anti-abuse heuristic."""
        with self._connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return False

            suspicious = False
            if user["device_fingerprint"]:
                shared = conn.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE device_fingerprint = ?",
                    (user["device_fingerprint"],),
                ).fetchone()["c"]
                suspicious = suspicious or shared >= same_signal_limit

            if user["last_ip"]:
                shared = conn.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE last_ip = ?",
                    (user["last_ip"],),
                ).fetchone()["c"]
                suspicious = suspicious or shared >= same_signal_limit

            conn.execute(
                "UPDATE users SET is_flagged_multiaccount = ?, updated_at = ? WHERE id = ?",
                (1 if suspicious else 0, self._as_iso(self._now()), user_id),
            )
            conn.commit()
            return suspicious

    def _create_wallet_transaction(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        amount: float,
        tx_type: str,
        idempotency_key: str,
        reference_type: str | None = None,
        reference_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> sqlite3.Row:
        existing = conn.execute(
            "SELECT * FROM wallet_transactions WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        if existing:
            return existing

        conn.execute(
            """
            INSERT INTO wallet_transactions(
                user_id, amount, tx_type, idempotency_key, reference_type, reference_id, metadata
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                tx_type,
                idempotency_key,
                reference_type,
                reference_id,
                json.dumps(metadata or {}),
            ),
        )
        conn.execute(
            "UPDATE users SET wallet_balance = wallet_balance + ?, updated_at = ? WHERE id = ?",
            (amount, self._as_iso(self._now()), user_id),
        )
        return conn.execute(
            "SELECT * FROM wallet_transactions WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()

    def get_balance(self, user_id: int) -> float:
        with self._connect() as conn:
            user = conn.execute("SELECT wallet_balance FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return 0.0
            return float(user["wallet_balance"])

    def process_spin(
        self,
        user_id: int,
        bet_amount: int,
        payout: int,
        round_id: str,
        symbol: str,
        multiplier: float,
        combo_details: dict[str, Any] | None = None,
    ) -> float:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")

            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise ValueError("User not found")

            if float(user["wallet_balance"]) < bet_amount:
                raise ValueError("Insufficient funds")

            metadata = {"symbol": symbol, "multiplier": multiplier, "combo": combo_details or {}}

            self._create_wallet_transaction(
                conn=conn,
                user_id=user_id,
                amount=-float(bet_amount),
                tx_type="spin_bet",
                idempotency_key=f"spin:{round_id}:bet",
                reference_type="spin_round",
                reference_id=round_id,
                metadata=metadata,
            )
            if payout > 0:
                self._create_wallet_transaction(
                    conn=conn,
                    user_id=user_id,
                    amount=float(payout),
                    tx_type="spin_win",
                    idempotency_key=f"spin:{round_id}:win",
                    reference_type="spin_round",
                    reference_id=round_id,
                    metadata=metadata,
                )

            self._record_spins(conn, user_id=user_id, spins=1, total_bet_amount=float(bet_amount))
            balance = conn.execute("SELECT wallet_balance FROM users WHERE id = ?", (user_id,)).fetchone()["wallet_balance"]
            conn.commit()
            return float(balance)

    def claim_daily_bonus(self, user_id: int, idempotency_key: str) -> tuple[bool, str, float]:
        now = self._now()
        today = now.date().isoformat()
        with self._connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return False, "User not found", 0.0
            if user["is_flagged_multiaccount"]:
                return False, "Account flagged by anti-abuse checks", 0.0

            cooldown_until = user["daily_cooldown_until"]
            if cooldown_until and datetime.fromisoformat(cooldown_until) > now:
                return False, "Daily bonus is on cooldown", 0.0

            existing = conn.execute(
                "SELECT * FROM daily_rewards WHERE user_id = ? AND claim_date = ?",
                (user_id, today),
            ).fetchone()
            if existing:
                return False, "Daily bonus already claimed today", existing["reward_amount"]

            prev = user["last_daily_claim_at"]
            streak = 1
            if prev:
                last_dt = datetime.fromisoformat(prev)
                days = (now.date() - last_dt.date()).days
                if days == 1:
                    streak = user["daily_streak"] + 1
                elif days == 0:
                    streak = user["daily_streak"]

            vip = conn.execute(
                """
                SELECT v.* FROM vip_tiers v
                JOIN users u ON u.vip_tier_id = v.id
                WHERE u.id = ?
                """,
                (user_id,),
            ).fetchone()
            multiplier = vip["daily_bonus_multiplier"] if vip else 1.0

            base = 10 + min(streak, 7) * 2
            reward = min(base * multiplier, self.limits.max_daily_reward)

            tx = self._create_wallet_transaction(
                conn,
                user_id=user_id,
                amount=reward,
                tx_type="daily_bonus",
                idempotency_key=idempotency_key,
                reference_type="daily_rewards",
                reference_id=f"{user_id}:{today}",
                metadata={"streak": streak, "multiplier": multiplier},
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO daily_rewards(user_id, claim_date, streak_day, reward_amount, idempotency_key)
                VALUES(?, ?, ?, ?, ?)
                """,
                (user_id, today, streak, reward, idempotency_key),
            )
            conn.execute(
                """
                UPDATE users
                SET daily_streak = ?,
                    last_daily_claim_at = ?,
                    daily_cooldown_until = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    streak,
                    self._as_iso(now),
                    self._as_iso(now + timedelta(hours=24)),
                    self._as_iso(now),
                    user_id,
                ),
            )
            conn.commit()
            return True, f"Daily reward claimed (tx#{tx['id']})", reward

    def seed_missions(self) -> None:
        missions = [
            ("spins_10", "10 Spins", "Сделай 10 спинов за день", "spins", 10, 15),
            ("spins_50", "50 Spins", "Сделай 50 спинов за день", "spins", 50, 90),
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO missions(code, name, description, objective_type, objective_target, reward_amount)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    objective_target = excluded.objective_target,
                    reward_amount = excluded.reward_amount,
                    is_active = 1
                """,
                missions,
            )
            conn.commit()

    def _get_or_create_user_mission(self, conn: sqlite3.Connection, user_id: int, mission_id: int, period_date: str) -> sqlite3.Row:
        conn.execute(
            """
            INSERT INTO user_missions(user_id, mission_id, period_date)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id, mission_id, period_date) DO NOTHING
            """,
            (user_id, mission_id, period_date),
        )
        return conn.execute(
            "SELECT * FROM user_missions WHERE user_id = ? AND mission_id = ? AND period_date = ?",
            (user_id, mission_id, period_date),
        ).fetchone()

    def record_spins(self, user_id: int, spins: int, total_bet_amount: float) -> None:
        with self._connect() as conn:
            self._record_spins(conn, user_id=user_id, spins=spins, total_bet_amount=total_bet_amount)
            conn.commit()

    def _record_spins(self, conn: sqlite3.Connection, user_id: int, spins: int, total_bet_amount: float) -> None:
        now = self._now()
        period = now.date().isoformat()
        conn.execute(
            """
            UPDATE users
            SET total_bet_turnover = total_bet_turnover + ?,
                updated_at = ?
            WHERE id = ?
            """,
            (total_bet_amount, self._as_iso(now), user_id),
        )
        missions = conn.execute(
            "SELECT * FROM missions WHERE is_active = 1 AND objective_type = 'spins'"
        ).fetchall()
        for m in missions:
            um = self._get_or_create_user_mission(conn, user_id, m["id"], period)
            if um["reward_claimed_at"]:
                continue
            new_progress = um["progress"] + spins
            completed_at = self._as_iso(now) if new_progress >= m["objective_target"] else None
            conn.execute(
                """
                UPDATE user_missions
                SET progress = ?, completed_at = COALESCE(completed_at, ?), updated_at = ?
                WHERE id = ?
                """,
                (new_progress, completed_at, self._as_iso(now), um["id"]),
            )

        self._update_user_vip_tier(conn, user_id)

    def _update_user_vip_tier(self, conn: sqlite3.Connection, user_id: int) -> None:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        tier = conn.execute(
            "SELECT * FROM vip_tiers WHERE min_turnover <= ? ORDER BY min_turnover DESC LIMIT 1",
            (user["total_bet_turnover"],),
        ).fetchone()
        if tier:
            conn.execute("UPDATE users SET vip_tier_id = ?, updated_at = ? WHERE id = ?", (tier["id"], self._as_iso(self._now()), user_id))

    def claim_mission_rewards(self, user_id: int, period_date: str, idempotency_prefix: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user or user["is_flagged_multiaccount"]:
                return []

            completed = conn.execute(
                """
                SELECT um.*, m.code, m.reward_amount
                FROM user_missions um
                JOIN missions m ON m.id = um.mission_id
                WHERE um.user_id = ? AND um.period_date = ?
                  AND um.completed_at IS NOT NULL AND um.reward_claimed_at IS NULL
                """,
                (user_id, period_date),
            ).fetchall()

            day_paid = conn.execute(
                """
                SELECT COALESCE(SUM(wt.amount), 0) AS s
                FROM wallet_transactions wt
                WHERE wt.user_id = ?
                  AND wt.tx_type = 'mission_reward'
                  AND date(wt.created_at) = ?
                """,
                (user_id, period_date),
            ).fetchone()["s"]

            awarded: list[dict[str, Any]] = []
            for row in completed:
                if day_paid >= self.limits.max_mission_reward_per_day:
                    break
                amount = min(row["reward_amount"], self.limits.max_mission_reward_per_day - day_paid)
                if amount <= 0:
                    continue
                idem = f"{idempotency_prefix}:{row['id']}"
                tx = self._create_wallet_transaction(
                    conn,
                    user_id,
                    amount,
                    "mission_reward",
                    idem,
                    reference_type="user_missions",
                    reference_id=str(row["id"]),
                    metadata={"mission": row["code"]},
                )
                conn.execute(
                    """
                    UPDATE user_missions
                    SET reward_claimed_at = ?, reward_tx_id = ?, idempotency_key = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (self._as_iso(self._now()), tx["id"], idem, self._as_iso(self._now()), row["id"]),
                )
                day_paid += amount
                awarded.append({"mission": row["code"], "amount": amount})

            conn.commit()
            return awarded

    def process_cashback_period(
        self,
        period_start: datetime,
        period_end: datetime,
        idempotency_prefix: str,
    ) -> list[dict[str, Any]]:
        """Periodic cashback by net-loss for the period."""
        with self._connect() as conn:
            users = conn.execute("SELECT * FROM users").fetchall()
            results: list[dict[str, Any]] = []
            for user in users:
                if user["is_flagged_multiaccount"]:
                    continue

                sums = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) AS spent,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS won
                    FROM wallet_transactions
                    WHERE user_id = ?
                      AND created_at >= ?
                      AND created_at < ?
                    """,
                    (user["id"], self._as_iso(period_start), self._as_iso(period_end)),
                ).fetchone()

                net_loss = max(sums["spent"] - sums["won"], 0)
                if net_loss <= 0:
                    continue

                tier = conn.execute("SELECT * FROM vip_tiers WHERE id = ?", (user["vip_tier_id"],)).fetchone()
                cashback_rate = tier["cashback_rate"] if tier else 0.01
                cashback = min(net_loss * cashback_rate, self.limits.max_cashback_per_period)
                if cashback <= 0:
                    continue

                idem = f"{idempotency_prefix}:{user['id']}:{period_start.date()}:{period_end.date()}"
                tx = self._create_wallet_transaction(
                    conn,
                    user_id=user["id"],
                    amount=cashback,
                    tx_type="cashback",
                    idempotency_key=idem,
                    reference_type="cashback_history",
                    reference_id=f"{period_start.date()}:{period_end.date()}",
                    metadata={"net_loss": net_loss, "rate": cashback_rate},
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cashback_history(
                        user_id, period_start, period_end, net_loss,
                        cashback_rate, cashback_amount, idempotency_key
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        self._as_iso(period_start),
                        self._as_iso(period_end),
                        net_loss,
                        cashback_rate,
                        cashback,
                        idem,
                    ),
                )
                results.append({"user_id": user["id"], "cashback": cashback, "tx_id": tx["id"]})

            conn.commit()
            return results

    def get_rewards_snapshot(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return {}
            vip = conn.execute("SELECT * FROM vip_tiers WHERE id = ?", (user["vip_tier_id"],)).fetchone()
            missions = conn.execute(
                """
                SELECT m.code, m.name, m.objective_target, um.progress, um.completed_at, um.reward_claimed_at
                FROM missions m
                LEFT JOIN user_missions um
                  ON um.mission_id = m.id AND um.user_id = ? AND um.period_date = ?
                WHERE m.is_active = 1
                """,
                (user_id, self._now().date().isoformat()),
            ).fetchall()

            return {
                "balance": user["wallet_balance"],
                "daily_streak": user["daily_streak"],
                "daily_cooldown_until": user["daily_cooldown_until"],
                "vip": vip["name"] if vip else "Bronze",
                "vip_turnover": user["total_bet_turnover"],
                "missions": [dict(m) for m in missions],
                "flagged_multiaccount": bool(user["is_flagged_multiaccount"]),
            }


def format_missions(missions: Iterable[dict[str, Any]]) -> str:
    lines = []
    for m in missions:
        progress = m.get("progress") or 0
        target = m["objective_target"]
        status = "✅" if m.get("reward_claimed_at") else ("🎯" if m.get("completed_at") else "⏳")
        lines.append(f"{status} {m['name']} — {progress}/{target}")
    return "\n".join(lines) if lines else "Активных миссий нет"
