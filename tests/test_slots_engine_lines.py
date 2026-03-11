from bot.services.slots_engine import SlotsEngine


class StubRNG:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = list(rows)

    def choices(self, population, weights, k):  # noqa: ANN001, ANN201
        row = self._rows.pop(0)
        assert len(row) == k
        return row


def test_calculate_payout_for_center_line_three_of_a_kind() -> None:
    engine = SlotsEngine()
    grid = [
        ["🍒", "🍋", "🍉"],
        ["7️⃣", "7️⃣", "7️⃣"],
        ["🍇", "🍋", "🍒"],
    ]

    win_lines, total_win, total_multiplier, symbol_hits = engine._calculate_paylines(grid, bet=10)

    assert len(win_lines) == 1
    assert win_lines[0].line_name == "center"
    assert win_lines[0].symbol == "7️⃣"
    assert total_multiplier == 20.0
    assert total_win == 200.0
    assert symbol_hits == {"7️⃣": 3}


def test_spin_uses_rng_and_counts_multiple_lines() -> None:
    engine = SlotsEngine()
    user_state = {"balance": 500.0}
    rng = StubRNG(
        [
            ["⭐", "⭐", "⭐"],
            ["⭐", "⭐", "⭐"],
            ["⭐", "⭐", "⭐"],
        ]
    )

    result = engine.spin(bet=10.0, user_state=user_state, rng=rng)

    assert len(result.win_lines) == 5
    assert result.multiplier == 60.0
    assert result.win_amount == 600.0
    assert result.symbol_hits == {"⭐": 15}
    assert result.balance_after == 1090.0
