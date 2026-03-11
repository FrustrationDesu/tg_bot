from dataclasses import dataclass

from bot.services.slots_engine import SlotsEngine


@dataclass(frozen=True)
class SpinResult:
    reels: list[list[str]]
    grid: list[list[str]]
    win_lines: list[dict[str, object]]
    multiplier: float
    symbol_hits: dict[str, int]


def spin_slot() -> SpinResult:
    """3x3 slot simulation with weighted symbols and line-based payouts."""
    engine = SlotsEngine()
    result = engine.spin(bet=1.0, user_state={"balance": 1_000.0})
    return SpinResult(
        reels=result.reels,
        grid=result.grid,
        win_lines=[
            {
                "line": line.line_name,
                "symbol": line.symbol,
                "count": line.count,
                "multiplier": line.multiplier,
            }
            for line in result.win_lines
        ],
        multiplier=result.multiplier,
        symbol_hits=result.symbol_hits,
    )
