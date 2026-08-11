import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import start as start_handler
from app.bot.middlewares.maintenance import MaintenanceMiddleware
from app.config.settings import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("access_hub")


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    dp.update.middleware(MaintenanceMiddleware())

    dp.include_router(start_handler.router)
    # روترهای فازهای بعد اینجا include می‌شوند:
    # dp.include_router(shop_handler.router)
    # dp.include_router(wallet_handler.router)
    # dp.include_router(admin_handler.router)

    return dp


async def run_polling() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    logger.info("Access Hub bot starting in POLLING mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook() -> None:
    """
    ساختار پایه برای Webhook - در فاز Deployment کامل می‌شود
    (aiohttp web app + SimpleRequestHandler).
    """
    raise NotImplementedError("Webhook mode در فاز Deployment پیاده‌سازی می‌شود.")


def main() -> None:
    if settings.run_mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
