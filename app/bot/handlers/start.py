from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.membership import membership_keyboard
from app.bot.keyboards.reply_menu import main_reply_keyboard
from app.config.settings import get_settings
from app.database.base import get_session
from app.services.membership_service import MembershipService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

router = Router(name="start")
settings = get_settings()


@router.message(CommandStart(), F.chat.type != "private")
async def handle_start_in_group(message: Message) -> None:
    """
    فروشگاه، کیف‌پول و ... فقط باید در چت خصوصی کاربر با ربات کار کنند؛
    اگر داخل گروه/گپ اجرا شوند، منوی ثابت (Reply Keyboard) برای کل گروه
    تنظیم می‌شود و همه‌ی اعضا می‌توانند دکمه‌های همدیگر را ببینند و بزنند.
    برای همین در گروه فقط یک لینک برای شروع در پیام خصوصی نمایش داده می‌شود.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 شروع خرید در پیوی", url=f"https://t.me/{settings.bot_username}?start=1")]
        ]
    )
    await message.reply("برای استفاده از Access Hub روی دکمه‌ی زیر بزنید 👇", reply_markup=keyboard)


@router.message(CommandStart(deep_link=True), F.chat.type == "private")
@router.message(CommandStart(), F.chat.type == "private")
async def handle_start(message: Message, command: CommandObject | None = None) -> None:
    # اگر کاربر از لینک دعوت (مثلاً https://t.me/BOT?start=ref_AH1234) وارد شده،
    # کد معرف را استخراج می‌کنیم تا referred_by درست ثبت شود (بدون این، شمارش
    # «بیشترین دعوت» در بخش تورنومنت همیشه صفر می‌ماند).
    referral_code: str | None = None
    payload = command.args if command else None
    if payload and payload.startswith("ref_"):
        referral_code = payload[len("ref_") :]

    bonus_result: dict | None = None
    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referral_code=referral_code,
        )

        settings_service = SettingsService(session)
        welcome_text = await settings_service.get("welcome_text") or ""
        required_channels = await MembershipService(session).get_active_channels()
        is_member = True
        if required_channels:
            is_member = await MembershipService(session).is_user_member_of_all(
                message.bot, message.from_user.id
            )

        # پاداش عضویت/دعوت فقط وقتی پرداخت می‌شود که عضویت کاربر در همه‌ی
        # کانال‌های اجباری (اگر کانالی تعریف شده باشد) قطعاً تأیید شده باشد.
        if is_member:
            bonus_result = await user_service.award_start_bonuses(user)

    welcome_text = welcome_text.replace("{shop_name}", "").strip()
    text = welcome_text or "خوش آمدید."

    if required_channels and not is_member:
        await message.answer(
            text + "\n\n📢 برای ادامه ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=membership_keyboard(required_channels),
        )
        return

    if bonus_result and bonus_result.get("join_bonus"):
        text += f"\n\n🎁 <b>{bonus_result['join_bonus']:,} Token</b> پاداش عضویت به شما تعلق گرفت!"

    await message.answer(text, reply_markup=main_reply_keyboard())

    if bonus_result and bonus_result.get("referral_bonus") and bonus_result.get("referrer_telegram_id"):
        try:
            await message.bot.send_message(
                chat_id=bonus_result["referrer_telegram_id"],
                text=(
                    f"🤝 یکی از دوستانتان با لینک دعوت شما به ربات پیوست و عضو شد!\n"
                    f"🎁 <b>{bonus_result['referral_bonus']:,} Token</b> به موجودی شما اضافه شد."
                ),
            )
        except Exception:
            pass
