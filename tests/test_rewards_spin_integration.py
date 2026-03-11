from pathlib import Path

from bot.services.rewards import RewardsService


def _make_rewards(tmp_path: Path) -> tuple[RewardsService, int]:
    db_path = tmp_path / "bot.db"
    rewards = RewardsService(str(db_path))
    schema_sql = Path("bot/db/schema.sql").read_text(encoding="utf-8")
    rewards.ensure_schema(schema_sql)
    rewards.ensure_default_vip_tiers()
    rewards.seed_missions()
    user = rewards.get_or_create_user(telegram_id=12345, username="tester")
    with rewards._connect() as conn:
        rewards._create_wallet_transaction(
            conn=conn,
            user_id=user["id"],
            amount=1000.0,
            tx_type="bootstrap",
            idempotency_key="bootstrap:12345",
        )
        conn.commit()
    return rewards, user["id"]


def test_spin_updates_db_balance_and_rewards_snapshot(tmp_path: Path):
    rewards, user_id = _make_rewards(tmp_path)

    before = rewards.get_balance(user_id)
    after = rewards.process_spin(
        user_id=user_id,
        bet_amount=100,
        payout=250,
        round_id="round-1",
        symbol="💎",
        multiplier=2.5,
    )

    assert before == 1000.0
    assert after == 1150.0
    assert rewards.get_balance(user_id) == 1150.0
    assert rewards.get_rewards_snapshot(user_id)["balance"] == 1150.0


def test_spin_progresses_missions_and_turnover(tmp_path: Path):
    rewards, user_id = _make_rewards(tmp_path)

    for i in range(10):
        rewards.process_spin(
            user_id=user_id,
            bet_amount=10,
            payout=0,
            round_id=f"round-{i}",
            symbol="💀",
            multiplier=0.0,
        )

    snapshot = rewards.get_rewards_snapshot(user_id)
    missions = {m["code"]: m for m in snapshot["missions"]}

    assert snapshot["vip_turnover"] == 100.0
    assert missions["spins_10"]["progress"] >= 10
    assert missions["spins_10"]["completed_at"] is not None
    assert missions["spins_50"]["progress"] >= 10


def test_balance_matches_rewards_after_spin(tmp_path: Path):
    rewards, user_id = _make_rewards(tmp_path)

    rewards.process_spin(
        user_id=user_id,
        bet_amount=200,
        payout=60,
        round_id="round-consistency",
        symbol="🍒",
        multiplier=0.3,
    )

    balance_value = rewards.get_balance(user_id)
    rewards_balance = float(rewards.get_rewards_snapshot(user_id)["balance"])

    assert balance_value == rewards_balance
