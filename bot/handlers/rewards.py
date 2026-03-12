from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers.ui import main_menu_keyboard
from bot.services.rewards import RewardsService, format_missions

router = Router()


def _telegram_user(message: Message) -> tuple[int, str | None]:
    user = message.from_user
    return int(user.id), getattr(user, "username", None)


@router.message(Command("rewards"))
async def rewards_command(message: Message, rewards: RewardsService) -> None:
    telegram_id, username = _telegram_user(message)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    rewards.run_multiaccount_heuristics(user["id"])

    data = rewards.get_rewards_snapshot(user["id"])
    if not data:
        await message.answer("Не удалось загрузить профиль наград.")
        return

    text = (
        f"💰 Balance: {data['balance']:.2f}\n"
        f"🔥 Streak: {data['daily_streak']}\n"
        f"👑 VIP: {data['vip']} (turnover: {data['vip_turnover']:.2f})\n"
        f"⚠️ Multiaccount flag: {'yes' if data['flagged_multiaccount'] else 'no'}"
    )
    await message.answer(text + "\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())


@router.message(Command("daily"))
async def daily_command(message: Message, rewards: RewardsService) -> None:
    telegram_id, username = _telegram_user(message)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    rewards.run_multiaccount_heuristics(user["id"])

    idem = f"daily:{telegram_id}:{datetime.now(timezone.utc).date().isoformat()}"
    ok, response_message, amount = rewards.claim_daily_bonus(user["id"], idem)
    prefix = "✅" if ok else "⚠️"
    await message.answer(f"{prefix} {response_message}. Amount: {amount:.2f}\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())


@router.message(Command("missions"))
async def missions_command(message: Message, rewards: RewardsService) -> None:
    telegram_id, username = _telegram_user(message)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)

    period = datetime.now(timezone.utc).date().isoformat()
    payouts = rewards.claim_mission_rewards(user["id"], period, f"mission:{telegram_id}:{period}")
    snapshot = rewards.get_rewards_snapshot(user["id"])

    msg = ["🎯 Missions:\n" + format_missions(snapshot.get("missions", []))]
    if payouts:
        paid = ", ".join(f"{p['mission']} +{p['amount']:.2f}" for p in payouts)
        msg.append(f"\n✅ Claimed: {paid}")

    await message.answer("\n".join(msg) + "\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())


@router.message(Command("vip"))
async def vip_command(message: Message, rewards: RewardsService) -> None:
    telegram_id, username = _telegram_user(message)
    user = rewards.get_or_create_user(telegram_id=telegram_id, username=username)
    data = rewards.get_rewards_snapshot(user["id"])

    text = (
        f"👑 Current VIP: {data.get('vip', 'Bronze')}\n"
        f"📊 Turnover: {data.get('vip_turnover', 0):.2f}\n"
        "VIP upgrades automatically based on betting turnover."
    )
    await message.answer(text + "\n\nВыберите действие в меню ниже.", reply_markup=main_menu_keyboard())
