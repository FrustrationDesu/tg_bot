from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYMBOLS = ["🍒", "🍋", "🍉", "🍇", "⭐", "7️⃣"]
SYMBOL_WEIGHTS = {
    "🍒": 34,
    "🍋": 24,
    "🍉": 18,
    "🍇": 12,
    "⭐": 8,
    "7️⃣": 4,
}

DEFAULT_REELS_ROWS = 3
DEFAULT_REELS_COLS = 3
DEFAULT_TARGET_RTP_MIN = 0.92
DEFAULT_TARGET_RTP_MAX = 0.98

_PAYTABLE_PATH = Path(__file__).resolve().parents[1] / "data" / "paytable.json"


@dataclass(slots=True)
class PayoutLine:
    line_index: int
    symbol: str
    count: int
    multiplier: float
    amount: float


@dataclass(slots=True)
class RTPSnapshot:
    total_bets: float
    total_payouts: float
    current_rtp: float
    target_min: float
    target_max: float
    alert: bool
    alert_message: str | None = None


@dataclass(slots=True)
class SpinResult:
    round_id: str
    timestamp: str
    reel: list[list[str]]
    paylines: list[PayoutLine]
    bet: float
    win_amount: float
    balance_before: float
    balance_after: float
    rtp: RTPSnapshot


@dataclass(slots=True)
class SlotsEngine:
    paytable_path: Path = _PAYTABLE_PATH
    symbols: list[str] = field(default_factory=lambda: list(SYMBOLS))
    symbol_weights: dict[str, int] = field(default_factory=lambda: dict(SYMBOL_WEIGHTS))
    _paytable: dict[str, dict[int, float]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._paytable = self._load_paytable()

    def _load_paytable(self) -> dict[str, dict[int, float]]:
        with self.paytable_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        paytable: dict[str, dict[int, float]] = {}
        for symbol, payouts in raw.items():
            paytable[symbol] = {int(k): float(v) for k, v in payouts.items()}
        return paytable

    def _generate_reel(self, rows: int, cols: int) -> list[list[str]]:
        weighted_pool = [self.symbol_weights[s] for s in self.symbols]
        return [
            random.choices(self.symbols, weights=weighted_pool, k=cols)
            for _ in range(rows)
        ]

    def _calculate_paylines(self, reel: list[list[str]], bet: float) -> tuple[list[PayoutLine], float]:
        paylines: list[PayoutLine] = []
        total_win = 0.0

        for idx, row in enumerate(reel):
            if not row:
                continue

            first_symbol = row[0]
            consecutive = 1
            for symbol in row[1:]:
                if symbol == first_symbol:
                    consecutive += 1
                else:
                    break

            multiplier = self._paytable.get(first_symbol, {}).get(consecutive, 0.0)
            if multiplier <= 0:
                continue

            line_win = bet * multiplier
            paylines.append(
                PayoutLine(
                    line_index=idx,
                    symbol=first_symbol,
                    count=consecutive,
                    multiplier=multiplier,
                    amount=round(line_win, 2),
                )
            )
            total_win += line_win

        return paylines, round(total_win, 2)

    def _build_rtp_snapshot(self, user_state: dict[str, Any]) -> RTPSnapshot:
        stats = user_state.setdefault("stats", {})
        total_bets = float(stats.get("total_bets", 0.0))
        total_payouts = float(stats.get("total_payouts", 0.0))

        target_min = float(user_state.get("rtp_target_min", DEFAULT_TARGET_RTP_MIN))
        target_max = float(user_state.get("rtp_target_max", DEFAULT_TARGET_RTP_MAX))

        current_rtp = (total_payouts / total_bets) if total_bets > 0 else 0.0
        out_of_range = not (target_min <= current_rtp <= target_max) if total_bets > 0 else False
        message = None
        if out_of_range:
            message = (
                f"RTP out of target range: {current_rtp:.4f} "
                f"(target {target_min:.4f}..{target_max:.4f})"
            )

        return RTPSnapshot(
            total_bets=round(total_bets, 2),
            total_payouts=round(total_payouts, 2),
            current_rtp=round(current_rtp, 4),
            target_min=target_min,
            target_max=target_max,
            alert=out_of_range,
            alert_message=message,
        )

    def spin(self, bet: float, user_state: dict[str, Any]) -> SpinResult:
        if bet <= 0:
            raise ValueError("Bet must be positive")

        balance = float(user_state.get("balance", 0.0))
        if balance < bet:
            raise ValueError("Insufficient balance")

        rows = int(user_state.get("reel_rows", DEFAULT_REELS_ROWS))
        cols = int(user_state.get("reel_cols", DEFAULT_REELS_COLS))
        if rows <= 0 or cols <= 0:
            raise ValueError("Reel dimensions must be positive")

        balance_before = round(balance, 2)
        balance_after_bet = balance_before - bet

        reel = self._generate_reel(rows=rows, cols=cols)
        paylines, win_amount = self._calculate_paylines(reel=reel, bet=bet)

        final_balance = round(balance_after_bet + win_amount, 2)

        user_state["balance"] = final_balance
        stats = user_state.setdefault("stats", {})
        stats["total_bets"] = round(float(stats.get("total_bets", 0.0)) + bet, 2)
        stats["total_payouts"] = round(float(stats.get("total_payouts", 0.0)) + win_amount, 2)

        round_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        rtp_snapshot = self._build_rtp_snapshot(user_state)

        return SpinResult(
            round_id=round_id,
            timestamp=timestamp,
            reel=reel,
            paylines=paylines,
            bet=round(bet, 2),
            win_amount=win_amount,
            balance_before=balance_before,
            balance_after=final_balance,
            rtp=rtp_snapshot,
        )


def spin(bet: float, user_state: dict[str, Any]) -> SpinResult:
    """Convenience wrapper for single spin calls."""
    engine = SlotsEngine()
    return engine.spin(bet=bet, user_state=user_state)
