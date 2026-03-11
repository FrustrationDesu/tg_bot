from __future__ import annotations

from datetime import datetime
from typing import Any

from bot.services.rewards import RewardsService, format_missions


def _telegram_user(update: Any) -> tuple[int, str | None]:
    user = update.effective_user
    return int(user.id), getattr(user, "username", None)


async def rewards_command(update: Any, context: Any) -> None:
    telegram_id, username = _telegram_user(update)
    service: RewardsService = context.bot_data["rewards_service"]
    user = service.get_or_create_user(telegram_id=telegram_id, username=username)
    service.run_multiaccount_heuristics(user["id"])

    data = service.get_rewards_snapshot(user["id"])
    if not data:
        await update.message.reply_text("Не удалось загрузить профиль наград.")
        return

    text = (
        f"💰 Balance: {data['balance']:.2f}\n"
        f"🔥 Streak: {data['daily_streak']}\n"
        f"👑 VIP: {data['vip']} (turnover: {data['vip_turnover']:.2f})\n"
        f"⚠️ Multiaccount flag: {'yes' if data['flagged_multiaccount'] else 'no'}"
    )
    await update.message.reply_text(text)


async def daily_command(update: Any, context: Any) -> None:
    telegram_id, username = _telegram_user(update)
    service: RewardsService = context.bot_data["rewards_service"]
    user = service.get_or_create_user(telegram_id=telegram_id, username=username)
    service.run_multiaccount_heuristics(user["id"])

    idem = f"daily:{telegram_id}:{datetime.utcnow().date().isoformat()}"
    ok, message, amount = service.claim_daily_bonus(user["id"], idem)
    prefix = "✅" if ok else "⚠️"
    await update.message.reply_text(f"{prefix} {message}. Amount: {amount:.2f}")


async def missions_command(update: Any, context: Any) -> None:
    telegram_id, username = _telegram_user(update)
    service: RewardsService = context.bot_data["rewards_service"]
    user = service.get_or_create_user(telegram_id=telegram_id, username=username)

    period = datetime.utcnow().date().isoformat()
    payouts = service.claim_mission_rewards(user["id"], period, f"mission:{telegram_id}:{period}")
    snapshot = service.get_rewards_snapshot(user["id"])

    msg = ["🎯 Missions:\n" + format_missions(snapshot.get("missions", []))]
    if payouts:
        paid = ", ".join(f"{p['mission']} +{p['amount']:.2f}" for p in payouts)
        msg.append(f"\n✅ Claimed: {paid}")

    await update.message.reply_text("\n".join(msg))


async def vip_command(update: Any, context: Any) -> None:
    telegram_id, username = _telegram_user(update)
    service: RewardsService = context.bot_data["rewards_service"]
    user = service.get_or_create_user(telegram_id=telegram_id, username=username)
    data = service.get_rewards_snapshot(user["id"])

    text = (
        f"👑 Current VIP: {data.get('vip', 'Bronze')}\n"
        f"📊 Turnover: {data.get('vip_turnover', 0):.2f}\n"
        "VIP upgrades automatically based on betting turnover."
    )
    await update.message.reply_text(text)


def register_rewards_handlers(application: Any) -> None:
    """
    Optional helper for python-telegram-bot applications.

    Example:
        from telegram.ext import CommandHandler
        application.add_handler(CommandHandler("rewards", rewards_command))
    """

    from telegram.ext import CommandHandler

    application.add_handler(CommandHandler("rewards", rewards_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("missions", missions_command))
    application.add_handler(CommandHandler("vip", vip_command))
