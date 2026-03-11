from collections import defaultdict


class WalletService:
    def __init__(self, initial_balance: int = 1000):
        self._balances = defaultdict(lambda: initial_balance)

    def get_balance(self, user_id: int) -> int:
        return self._balances[user_id]

    def apply_bet(self, user_id: int, amount: int, payout: int) -> int:
        self._balances[user_id] -= amount
        self._balances[user_id] += payout
        return self._balances[user_id]
