import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.services.game import spin_slot
from bot.services.validation import validate_bet
from bot.services.wallet import WalletService

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет! Это слот-бот.\n"
        "Команды:\n"
        "/balance — показать баланс\n"
        "/spin <ставка> — сделать спин"
    )


@router.message(Command("balance"))
async def balance_handler(message: Message, wallet: WalletService) -> None:
    balance = wallet.get_balance(message.from_user.id)
    await message.answer(f"Ваш баланс: {balance}")


@router.message(Command("spin"))
async def spin_handler(message: Message, wallet: WalletService, settings: Settings) -> None:
    args = (message.text or "").split(maxsplit=1)
    raw_amount = args[1] if len(args) > 1 else None

    user_id = message.from_user.id
    current_balance = wallet.get_balance(user_id)

    is_valid, payload = validate_bet(raw_amount, settings.min_bet, settings.max_bet, current_balance)
    if not is_valid:
        await message.answer(payload)
        return

    amount = payload
    result = spin_slot()
    payout = int(amount * result.multiplier)
    new_balance = wallet.apply_bet(user_id=user_id, amount=amount, payout=payout)

    logger.info(
        "Spin processed user_id=%s amount=%s symbol=%s multiplier=%.2f payout=%s balance=%s",
        user_id,
        amount,
        result.symbol,
        result.multiplier,
        payout,
        new_balance,
    )

    await message.answer(
        f"Выпало {result.symbol}\n"
        f"Множитель: x{result.multiplier}\n"
        f"Выплата: {payout}\n"
        f"Новый баланс: {new_balance}"
    )
