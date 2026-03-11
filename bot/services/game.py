import random
from dataclasses import dataclass


@dataclass(frozen=True)
class SpinResult:
    symbol: str
    multiplier: float


def spin_slot() -> SpinResult:
    """Simple slot simulation with weighted payouts."""
    roll = random.random()
    if roll < 0.03:
        return SpinResult(symbol="💎", multiplier=5.0)
    if roll < 0.10:
        return SpinResult(symbol="⭐", multiplier=2.0)
    if roll < 0.30:
        return SpinResult(symbol="🍒", multiplier=1.2)
    return SpinResult(symbol="💀", multiplier=0.0)
