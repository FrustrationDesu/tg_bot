import logging
from uuid import uuid4

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import Settings
from bot.handlers.ui import main_menu_keyboard
from bot.services.game import spin_slot
from bot.services.rewards import RewardsService
from bot.services.validation import validate_bet

logger = logging.getLogger(__name__)
router = Router()


BET_OPTIONS = (10, 25, 50, 100)


def spin_bet_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(amount), callback_data=f"spin_bet:{amount}") for amount in BET_OPTIONS]
        ]
    )


@router.message(Command("start"))
async def start_handler(message: Message, rewards: RewardsService) -> None:
    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    balance = rewards.get_balance(user["id"])
    has_welcome = rewards.has_welcome_bonus(telegram_id)

    cta = "🎁 Забрать ежедневный бонус: /daily"
    if balance <= 0:
        cta = "🆓 Получить стартовый бонус: /start"
        if has_welcome:
            cta = "🎁 Забрать ежедневный бонус: /daily"

    await message.answer(
        "Привет! Это слот-бот.\n"
        f"Ваш баланс: {balance:.2f}\n\n"
        "Команды оставлены как fallback.\n"
        "Выберите действие в меню ниже.\n\n"
        f"{cta}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text.casefold().in_({"старт", "start"}))
async def text_start_handler(message: Message, rewards: RewardsService) -> None:
    await start_handler(message, rewards)


@router.message(Command("balance"))
async def balance_handler(message: Message, rewards: RewardsService) -> None:
    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    balance = rewards.get_balance(user["id"])
    await message.answer(f"Ваш баланс: {balance}\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())


async def _process_spin(message: Message, rewards: RewardsService, settings: Settings, raw_amount: str | None) -> None:
    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    user_id = user["id"]
    current_balance = int(rewards.get_balance(user_id))

    is_valid, payload = validate_bet(raw_amount, settings.min_bet, settings.max_bet, current_balance)
    if not is_valid:
        if current_balance <= 0:
            await message.answer(
                f"{payload}\n\n🆓 Получить стартовый бонус: /start\n🎁 Забрать ежедневный бонус: /daily\n\nВыберите действие в меню ниже.",
                reply_markup=main_menu_keyboard(),
            )
            return
        await message.answer(f"{payload}\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())
        return

    amount = payload
    result = spin_slot()
    payout = int(amount * result.multiplier)
    primary_symbol = result.win_lines[0]["symbol"] if result.win_lines else "—"
    round_id = f"{telegram_id}:{uuid4().hex}"
    new_balance = rewards.process_spin(
        user_id=user_id,
        bet_amount=amount,
        payout=payout,
        round_id=round_id,
        symbol=primary_symbol,
        multiplier=result.multiplier,
        combo_details={
            "reels": result.reels,
            "win_lines": result.win_lines,
            "symbol_hits": result.symbol_hits,
        },
    )

    logger.info(
        "Spin processed user_id=%s amount=%s symbol=%s multiplier=%.2f payout=%s balance=%s",
        user_id,
        amount,
        primary_symbol,
        result.multiplier,
        payout,
        new_balance,
    )

    grid_lines = [" ".join(row) for row in result.grid]
    wins = "\n".join(f"- {line['line']}: {line['symbol']} x{line['multiplier']}" for line in result.win_lines) or "- нет"

    await message.answer(
        "Поле:\n"
        + "\n".join(grid_lines)
        + "\n\nЛинии выигрыша:\n"
        + wins
        + f"\n\nОбщий множитель: x{result.multiplier}"
        + f"\nВыплата: {payout}"
        + f"\nНовый баланс: {new_balance}\n\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("spin"))
async def spin_handler(message: Message, rewards: RewardsService, settings: Settings) -> None:
    args = (message.text or "").split(maxsplit=1)
    raw_amount = args[1] if len(args) > 1 else None
    await _process_spin(message, rewards, settings, raw_amount)


@router.callback_query(F.data.startswith("spin_bet:"))
async def spin_bet_callback_handler(callback: CallbackQuery, rewards: RewardsService, settings: Settings) -> None:
    if not callback.message:
        await callback.answer("Сообщение недоступно", show_alert=True)
        return

    bet = callback.data.split(":", maxsplit=1)[1]
    await _process_spin(callback.message, rewards, settings, bet)
    await callback.answer()
