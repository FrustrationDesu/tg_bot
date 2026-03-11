import asyncio
import logging

from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import ConfigError, Settings, get_settings
from bot.handlers import router
from bot.logger import setup_logger
from bot.services.wallet import WalletService

logger = logging.getLogger(__name__)


class AppContextMiddleware(BaseMiddleware):
    def __init__(self, wallet: WalletService, settings: Settings):
        self.wallet = wallet
        self.settings = settings

    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["wallet"] = self.wallet
        data["settings"] = self.settings
        return await handler(event, data)


async def start_polling(bot: Bot, dp: Dispatcher) -> None:
    await dp.start_polling(bot)


async def start_webhook(bot: Bot, dp: Dispatcher, settings: Settings) -> None:
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    await bot.set_webhook(url=f"{settings.webhook_url}{settings.webhook_path}")
    logger.info("Webhook configured at %s%s", settings.webhook_url, settings.webhook_path)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.host, settings.port)
    await site.start()
    logger.info("Webhook server started on %s:%s", settings.host, settings.port)

    while True:
        await asyncio.sleep(3600)


async def main() -> None:
    setup_logger()

    try:
        settings = get_settings()
    except ConfigError:
        logger.exception("Invalid configuration")
        raise

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    wallet = WalletService()
    dp.update.middleware(AppContextMiddleware(wallet=wallet, settings=settings))
    dp.include_router(router)

    logger.info("Bot starting with min_bet=%s max_bet=%s db_url=%s", settings.min_bet, settings.max_bet, settings.db_url)

    if settings.webhook_url:
        await start_webhook(bot, dp, settings)
    else:
        await start_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())
