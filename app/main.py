import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.bot.handlers import account as account_handler
from app.bot.handlers import membership as membership_handler
from app.bot.handlers import shop as shop_handler
from app.bot.handlers import start as start_handler
from app.bot.middlewares.maintenance import MaintenanceMiddleware
from app.bot.middlewares.membership import MembershipMiddleware
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
    dp.update.middleware(MembershipMiddleware())

    dp.include_router(start_handler.router)
    dp.include_router(membership_handler.router)
    dp.include_router(shop_handler.router)
    dp.include_router(account_handler.router)
    # روترهای فازهای بعد اینجا include می‌شوند:
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


async def health_check(_: web.Request) -> web.Response:
    """Render/هر پلتفرمی برای بررسی زنده‌بودن سرویس به این مسیر درخواست می‌زند."""
    return web.Response(text="Access Hub bot is running.")


async def run_webhook() -> None:
    """
    اجرای ربات به‌صورت Web Service (مناسب برای پلن رایگان Render که
    Background Worker رایگان ندارد). Render آدرس عمومی سرویس را خودکار
    در متغیر محیطی RENDER_EXTERNAL_URL قرار می‌دهد، پس نیازی به تنظیم
    دستی WEBHOOK_BASE_URL روی Render نیست (فقط برای دیپلوی‌های دیگر لازم است).
    """
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    base_url = settings.webhook_base_url or os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        raise RuntimeError(
            "آدرس عمومی سرویس پیدا نشد. WEBHOOK_BASE_URL را در Environment Variables تنظیم کن."
        )
    webhook_url = base_url.rstrip("/") + settings.webhook_path

    logger.info(f"Access Hub bot starting in WEBHOOK mode -> {webhook_url}")
    await bot.set_webhook(webhook_url, drop_pending_updates=True)

    app = web.Application()
    app.router.add_get("/", health_check)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", settings.webapp_port))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, port)
    await site.start()

    logger.info(f"Web service listening on {settings.webapp_host}:{port}")
    await asyncio.Event().wait()  # برای همیشه زنده بماند


def main() -> None:
    if settings.run_mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
