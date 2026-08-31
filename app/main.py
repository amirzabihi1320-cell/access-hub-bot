import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.bot.handlers import admin as admin_handler
from app.bot.handlers import main_menu as main_menu_handler
from app.bot.handlers import membership as membership_handler
from app.bot.handlers import orders as orders_handler
from app.bot.handlers import shop as shop_handler
from app.bot.handlers import start as start_handler
from app.bot.handlers import tournament as tournament_handler
from app.bot.handlers import wallet as wallet_handler
from app.bot.handlers import games as games_handler
from app.bot.middlewares.blocked import BlockedUserMiddleware
from app.bot.middlewares.maintenance import MaintenanceMiddleware
from app.bot.middlewares.membership import MembershipMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.config.settings import get_settings
from app.database.seed import seed_initial_data
from app.services.game_service import scheduler_loop

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("access_hub")


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # ترتیب اهمیت دارد: ابتدا ضدفلاد (سبک‌ترین/زودترین رد کردن اسپم)، بعد
    # مسدودی کاربر، بعد Maintenance، در آخر عضویت اجباری (سنگین‌ترین چون
    # با API تلگرام تماس می‌گیرد).
    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(BlockedUserMiddleware())
    dp.update.middleware(MaintenanceMiddleware())
    dp.update.middleware(MembershipMiddleware())

    dp.include_router(start_handler.router)
    dp.include_router(membership_handler.router)
    dp.include_router(main_menu_handler.router)
    dp.include_router(shop_handler.router)
    dp.include_router(wallet_handler.router)
    dp.include_router(games_handler.router)
    dp.include_router(orders_handler.router)
    dp.include_router(tournament_handler.router)
    dp.include_router(admin_handler.router)

    return dp


async def _set_bot_commands(bot: Bot) -> None:
    """
    این‌ها همون کامندهایی‌ان که با زدن دکمه‌ی سه‌خط (☰) کنار جعبه‌ی تایپ
    همیشه در دسترس کاربر می‌مونن — /start همیشه اونجاست، صرف‌نظر از این‌که
    کاربر کجای مکالمه باشه یا کیبورد Reply رو بسته باشه.
    """
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 شروع / منوی اصلی"),
    ])


async def run_polling() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()

    logger.info("Access Hub bot starting in POLLING mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    await _set_bot_commands(bot)
    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)
        await bot.session.close()


async def health_check(_: web.Request) -> web.Response:
    """Render/هر پلتفرمی برای بررسی زنده‌بودن سرویس به این مسیر درخواست می‌زند."""
    return web.Response(text="Access Hub bot is running.")

async def tronado_webhook(request: web.Request) -> web.Response:
    """Receive and verify Tronado IPN using the raw request body.

    The signature is checked before JSON parsing/financial settlement.
    Duplicate callbacks are safe because PaymentService uses the payment_id
    and a unique wallet ledger reference.
    """
    from app.database.base import get_session
    from app.services.payment_service import PaymentService

    raw_body = await request.read()
    signature = request.headers.get("X-Tronado-Sig", "")
    try:
        async with get_session() as session:
            await PaymentService(session).handle_tronado_webhook(raw_body, signature)
    except Exception as exc:
        logger.warning("Tronado webhook rejected/failed: %s", exc)
        return web.json_response({"ok": False, "error": "invalid_or_unprocessed_webhook"}, status=400)
    return web.json_response({"ok": True})


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
    await _set_bot_commands(bot)

    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_post("/payments/tronado/webhook", tronado_webhook)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", settings.webapp_port))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, port)
    await site.start()

    logger.info(f"Web service listening on {settings.webapp_host}:{port}")
    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    try:
        await asyncio.Event().wait()  # برای همیشه زنده بماند
    finally:
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)
        await runner.cleanup()
        await bot.session.close()


def main() -> None:
    asyncio.run(seed_initial_data())

    if settings.run_mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
