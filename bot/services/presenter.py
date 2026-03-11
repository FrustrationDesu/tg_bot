from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SPIN_ACTION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Крутить ещё", callback_data="spin:again")],
        [InlineKeyboardButton(text="➕ Повысить ставку", callback_data="spin:raise")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance:show")],
    ]
)


def render_spin_result(*, reel_symbol: str, payout: int, balance_before: int, balance_after: int) -> str:
    """Render a multi-line slot machine screen for the spin response."""
    reels = [
        "| 🍒 | 🔔 | 🍋 |",
        f"| 🍋 | {reel_symbol} | 🍒 |",
        "| 🔔 | 🍒 | 🍋 |",
    ]
    result_line = "✅ Выигрыш" if payout > 0 else "❌ Мимо"
    return (
        "🎰 Слот-машина\n\n"
        f"{reels[0]}\n"
        f"{reels[1]}\n"
        f"{reels[2]}\n\n"
        f"{result_line}\n"
        f"💸 Выплата: {payout}\n"
        f"Баланс: {balance_before} → {balance_after}"
    )
