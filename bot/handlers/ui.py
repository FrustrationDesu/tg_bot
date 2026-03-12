from aiogram import F, Router
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.services.rewards import RewardsService

router = Router()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Спин"), KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="🎁 Daily"), KeyboardButton(text="🎯 Миссии")],
            [KeyboardButton(text="👑 VIP")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "🎰 Спин")
async def spin_button_handler(message: Message, rewards: RewardsService) -> None:
    telegram_id = int(message.from_user.id)
    username = getattr(message.from_user, "username", None)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    balance = rewards.get_balance(user["id"])

    if balance <= 0:
        await message.answer(
            "Баланс пустой.\n"
            "🆓 Получить стартовый бонус: /start\n"
            "🎁 Забрать ежедневный бонус: /daily\n\n"
            "Выберите действие в меню ниже.",
            reply_markup=main_menu_keyboard(),
        )
        return

    from bot.handlers.commands import spin_bet_keyboard

    await message.answer("Выберите ставку:", reply_markup=spin_bet_keyboard())


@router.message(F.text == "💰 Баланс")
async def balance_button_handler(message: Message, rewards: RewardsService) -> None:
    from bot.handlers.commands import balance_handler

    await balance_handler(message, rewards)


@router.message(F.text == "🎁 Daily")
async def daily_button_handler(message: Message, rewards: RewardsService) -> None:
    from bot.handlers.rewards import daily_command

    await daily_command(message, rewards)


@router.message(F.text == "🎯 Миссии")
async def missions_button_handler(message: Message, rewards: RewardsService) -> None:
    from bot.handlers.rewards import missions_command

    await missions_command(message, rewards)


@router.message(F.text == "👑 VIP")
async def vip_button_handler(message: Message, rewards: RewardsService) -> None:
    from bot.handlers.rewards import vip_command

    await vip_command(message, rewards)
