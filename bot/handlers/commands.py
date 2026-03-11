import logging
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import Settings
from bot.services.game import spin_slot
from bot.services.presenter import SPIN_ACTION_KEYBOARD, render_spin_result
from bot.services.validation import validate_bet
from bot.services.rewards import RewardsService

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


@router.message(F.text.casefold().in_({"старт", "start"}))
async def text_start_handler(message: Message) -> None:
    await message.answer(
        "Привет! Это слот-бот.\n"
        "Команды:\n"
        "/balance — показать баланс\n"
        "/spin <ставка> — сделать спин\n\n"
        "Подсказка: основная команда запуска — /start"
    )


@router.message(Command("balance"))
async def balance_handler(message: Message, rewards: RewardsService) -> None:
    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    balance = rewards.get_balance(user["id"])
    await message.answer(f"Ваш баланс: {balance}")


@router.message(Command("spin"))
async def spin_handler(message: Message, rewards: RewardsService, settings: Settings) -> None:
    args = (message.text or "").split(maxsplit=1)
    raw_amount = args[1] if len(args) > 1 else None

    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    user_id = user["id"]
    current_balance = int(rewards.get_balance(user_id))

    is_valid, payload = validate_bet(raw_amount, settings.min_bet, settings.max_bet, current_balance)
    if not is_valid:
        await message.answer(payload)
        return

    amount = payload
    result = spin_slot()
    payout = int(amount * result.multiplier)
    round_id = f"{telegram_id}:{uuid4().hex}"
    new_balance = rewards.process_spin(
        user_id=user_id,
        bet_amount=amount,
        payout=payout,
        round_id=round_id,
        symbol=result.symbol,
        multiplier=result.multiplier,
    )

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
        render_spin_result(
            reel_symbol=result.symbol,
            payout=payout,
            balance_before=current_balance,
            balance_after=new_balance,
        ),
        reply_markup=SPIN_ACTION_KEYBOARD,
    )
