

def validate_bet(raw_amount: str | None, min_bet: int, max_bet: int, balance: int) -> tuple[bool, str | int]:
    if not raw_amount:
        return False, "Укажите ставку: /spin <amount>"

    try:
        amount = int(raw_amount)
    except ValueError:
        return False, "Ставка должна быть целым числом."

    if amount < min_bet:
        return False, f"Минимальная ставка: {min_bet}."

    if amount > max_bet:
        return False, f"Максимальная ставка: {max_bet}."

    if amount > balance:
        return False, f"Недостаточно средств. Ваш баланс: {balance}. Нажмите 🎁 Daily (/daily), чтобы пополнить баланс, или используйте 🆓 /start для стартового бонуса."

    return True, amount
