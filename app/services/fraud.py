from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import GameRound


MAX_BET_BY_LEVEL = {
    1: 10,
    2: 25,
    3: 50,
    4: 100,
    5: 250,
}


def max_bet_for_level(level: int) -> int:
    return MAX_BET_BY_LEVEL.get(level, 500)


def check_spin_rate_limit(db: Session, user_id: int, limit_per_minute: int) -> bool:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=1)
    statement = (
        select(func.count(GameRound.id))
        .where(GameRound.user_id == user_id)
        .where(GameRound.created_at >= threshold)
    )
    count = db.execute(statement).scalar_one()
    return count < limit_per_minute
