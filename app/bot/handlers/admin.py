"""
فاز ۵: پنل ادمین (بخش ۲۷-۲۹، ۳۹، ۵۴ سند).

فعلاً یک سطح دسترسی داریم: هر آیدی داخل ADMIN_IDS ادمین کامل است
(Role-based Permission با جدول admin_roles در فاز بعد اضافه می‌شود).
همه‌ی متن‌ها/تنظیمات حساس (شماره کارت، نام فروشگاه و ...) از همینجا
بدون تغییر کد قابل ویرایش‌اند.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from app.bot.keyboards.admin import (
    EDITABLE_SETTINGS,
    admin_back_keyboard,
    admin_categories_keyboard,
    admin_category_delete_confirm_keyboard,
    admin_channels_keyboard,
    admin_dashboard_keyboard,
    admin_product_category_pick_keyboard,
    admin_product_delete_confirm_keyboard,
    admin_product_detail_keyboard,
    admin_product_type_pick_keyboard,
    admin_products_keyboard,
    admin_settings_keyboard,
    button_columns_keyboard,
)
from app.bot.keyboards.wallet import admin_deposit_decision_keyboard
from app.bot.states.admin_states import AdminStates
from app.config.settings import get_settings
from app.core.enums import DepositRequestStatus, OrderStatus
from app.database.base import get_session
from app.models.order import Order
from app.models.product import Product
from app.models.required_channel import RequiredChannel
from app.models.user import User
from app.services.category_service import CategoryService
from app.services.deposit_service import DepositService
from app.services.membership_service import MembershipService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

router = Router(name="admin")
settings = get_settings()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


async def _dashboard_text(session) -> str:
    users_count = await UserService(session).count_all()
    orders_count = await OrderService(session).count_all()
    pending_orders = await OrderService(session).count_pending()
    revenue = await OrderService(session).total_revenue()
    pending_deposits = await DepositService(session).count_pending()

    return (
        "📊 <b>داشبورد</b>\n\n"
        f"👥 کاربران: {users_count}\n"
        f"📦 کل سفارش‌ها: {orders_count}\n"
        f"🔄 سفارش‌های در انتظار تحویل: {pending_orders}\n"
        f"💰 درآمد کل: {revenue:,} تومان\n"
        f"💳 شارژهای در انتظار تأیید: {pending_deposits}"
    )


@router.message(Command("admin"))
async def handle_admin_entry(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    async with get_session() as session:
        text = await _dashboard_text(session)
    await message.answer(text, reply_markup=admin_dashboard_keyboard())


@router.callback_query(F.data == "admin:menu")
async def handle_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.clear()
    async with get_session() as session:
        text = await _dashboard_text(session)
    await callback.message.edit_text(text, reply_markup=admin_dashboard_keyboard())
    await callback.answer()


# ---------- محصولات ----------


@router.callback_query(F.data == "admin:products")
async def handle_admin_products(callback: CallbackQuery) -> None:
    async with get_session() as session:
        products = await ProductService(session).list_all()
    await callback.message.edit_text("🛍 <b>محصولات</b>", reply_markup=admin_products_keyboard(products))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:view:"))
async def handle_admin_product_view(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        product = await ProductService(session).get(product_id)
    if not product:
        await callback.answer("محصول پیدا نشد.", show_alert=True)
        return
    price = product.fixed_price if product.product_type == "FIXED" else product.unit_price
    status_label = "🟢 فعال" if product.status else "🔴 غیرفعال"
    text = f"🛍 <b>{product.name}</b>\n\nقیمت: {price:,} تومان\nوضعیت: {status_label}"
    await callback.message.edit_text(text, reply_markup=admin_product_detail_keyboard(product))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:toggle:"))
async def handle_admin_product_toggle(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        product = await ProductService(session).toggle_status(product_id)
        price = product.fixed_price if product.product_type == "FIXED" else product.unit_price
    status_label = "🟢 فعال" if product.status else "🔴 غیرفعال"
    text = f"🛍 <b>{product.name}</b>\n\nقیمت: {price:,} تومان\nوضعیت: {status_label}"
    await callback.message.edit_text(text, reply_markup=admin_product_detail_keyboard(product))
    await callback.answer("ثبت شد ✅")


@router.callback_query(F.data.startswith("admin:product:price:"))
async def handle_admin_product_price_start(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[3])
    await state.set_state(AdminStates.WAITING_NEW_PRICE)
    await state.update_data(product_id=product_id)
    await callback.message.edit_text("💰 قیمت جدید را به تومان وارد کنید:", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.message(AdminStates.WAITING_NEW_PRICE, F.text)
async def handle_admin_product_price_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(",", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❗️ یک عدد صحیح و مثبت وارد کنید.")
        return

    data = await state.get_data()
    product_id = data.get("product_id")
    async with get_session() as session:
        try:
            product = await ProductService(session).update_price(product_id, int(raw))
        except ValueError as e:
            await message.answer(f"❌ {e}")
            return
    await state.clear()
    await message.answer(f"✅ قیمت «{product.name}» به‌روزرسانی شد: {int(raw):,} تومان")


@router.callback_query(F.data.startswith("admin:product:del:"))
async def handle_admin_product_delete_ask(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        product = await ProductService(session).get(product_id)
    if not product:
        await callback.answer("محصول پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ آیا از حذف محصول «{product.name}» مطمئن هستید؟\nاین کار قابل بازگشت نیست.",
        reply_markup=admin_product_delete_confirm_keyboard(product_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:delyes:"))
async def handle_admin_product_delete_confirm(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        try:
            await ProductService(session).delete(product_id)
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return
        products = await ProductService(session).list_all()
    await callback.message.edit_text("✅ محصول حذف شد.\n\n🛍 <b>محصولات</b>", reply_markup=admin_products_keyboard(products))
    await callback.answer()


# ---------- افزودن محصول ----------


@router.callback_query(F.data == "admin:product:add")
async def handle_admin_product_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.WAITING_PRODUCT_NAME)
    await callback.message.edit_text("🛍 نام محصول جدید را بفرستید:", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.message(AdminStates.WAITING_PRODUCT_NAME, F.text)
async def handle_admin_product_add_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(product_name=message.text.strip())
    async with get_session() as session:
        categories = await CategoryService(session).list_all()
    if not categories:
        await state.clear()
        await message.answer("❗️ ابتدا باید حداقل یک دسته‌بندی بسازید.")
        return
    await message.answer("📂 دسته‌بندی را انتخاب کنید:", reply_markup=admin_product_category_pick_keyboard(categories))


@router.callback_query(F.data.startswith("admin:product:add:category:"))
async def handle_admin_product_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[4])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("⚙️ نوع قیمت‌گذاری را انتخاب کنید:", reply_markup=admin_product_type_pick_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:add:type:"))
async def handle_admin_product_add_type(callback: CallbackQuery, state: FSMContext) -> None:
    product_type = callback.data.split(":", 4)[4]
    await state.update_data(product_type=product_type)

    if product_type == "FIXED":
        await state.set_state(AdminStates.WAITING_PRODUCT_FIXED_PRICE)
        await callback.message.edit_text("💰 قیمت را به تومان وارد کنید:")
    else:
        await state.set_state(AdminStates.WAITING_PRODUCT_UNIT_PRICE)
        await callback.message.edit_text("💰 قیمت هر واحد را به تومان وارد کنید:")
    await callback.answer()


def _parse_positive_int(text: str) -> int | None:
    raw = text.strip().replace(",", "")
    if not raw.isdigit() or int(raw) <= 0:
        return None
    return int(raw)


@router.message(AdminStates.WAITING_PRODUCT_FIXED_PRICE, F.text)
async def handle_admin_product_fixed_price(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    price = _parse_positive_int(message.text)
    if price is None:
        await message.answer("❗️ یک عدد صحیح و مثبت وارد کنید.")
        return

    await state.update_data(fixed_price=price)
    await state.set_state(AdminStates.WAITING_PRODUCT_BUTTON_COLUMNS)

    await message.answer(
        "📐 نحوه نمایش دکمه این محصول را انتخاب کنید:",
        reply_markup=button_columns_keyboard("admin:products"),
    )


@router.message(AdminStates.WAITING_PRODUCT_UNIT_PRICE, F.text)
async def handle_admin_product_unit_price(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    price = _parse_positive_int(message.text)
    if price is None:
        await message.answer("❗️ یک عدد صحیح و مثبت وارد کنید.")
        return
    await state.update_data(unit_price=price)
    await state.set_state(AdminStates.WAITING_PRODUCT_MIN_QTY)
    await message.answer("🔢 حداقل تعداد خرید را وارد کنید:")


@router.message(AdminStates.WAITING_PRODUCT_MIN_QTY, F.text)
async def handle_admin_product_min_qty(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    min_qty = _parse_positive_int(message.text)
    if min_qty is None:
        await message.answer("❗️ یک عدد صحیح و مثبت وارد کنید.")
        return
    await state.update_data(min_qty=min_qty)
    await state.set_state(AdminStates.WAITING_PRODUCT_MAX_QTY)
    await message.answer("🔢 حداکثر تعداد خرید را وارد کنید:")


@router.message(AdminStates.WAITING_PRODUCT_MAX_QTY, F.text)
async def handle_admin_product_max_qty(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    max_qty = _parse_positive_int(message.text)
    data = await state.get_data()
    if max_qty is None or max_qty < data.get("min_qty", 0):
        await message.answer("❗️ باید عددی صحیح و بزرگ‌تر یا مساوی حداقل باشد.")
        return

    await state.update_data(max_qty=max_qty)
    await state.set_state(AdminStates.WAITING_PRODUCT_BUTTON_COLUMNS)

    await message.answer(
        "📐 نحوه نمایش دکمه این محصول را انتخاب کنید:",
        reply_markup=button_columns_keyboard("admin:products"),
    )


# ---------- دسته‌بندی‌ها ----------


@router.callback_query(F.data == "admin:categories")
async def handle_admin_categories(callback: CallbackQuery) -> None:
    async with get_session() as session:
        categories = await CategoryService(session).list_all()
    await callback.message.edit_text(
        "📂 <b>دسته‌بندی‌ها</b>", reply_markup=admin_categories_keyboard(categories)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:category:toggle:"))
async def handle_admin_category_toggle(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        await CategoryService(session).toggle_status(category_id)
        categories = await CategoryService(session).list_all()
    await callback.message.edit_text(
        "📂 <b>دسته‌بندی‌ها</b>", reply_markup=admin_categories_keyboard(categories)
    )
    await callback.answer("ثبت شد ✅")


@router.callback_query(F.data == "admin:category:add")
async def handle_admin_category_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.WAITING_CATEGORY_NAME)
    await callback.message.edit_text("📂 نام دسته‌بندی جدید را بفرستید:", reply_markup=admin_back_keyboard())
    await callback.answer()


@router.message(AdminStates.WAITING_CATEGORY_NAME, F.text)
async def handle_admin_category_add_name(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(category_name=message.text.strip())
    await state.set_state(AdminStates.WAITING_CATEGORY_ICON)
    await message.answer("🔤 یک ایموجی برای آیکون بفرستید (یا «-» برای رد شدن):")


@router.message(AdminStates.WAITING_CATEGORY_ICON, F.text)
async def handle_admin_category_add_icon(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    icon = None if message.text.strip() == "-" else message.text.strip()

    await state.update_data(category_icon=icon)
    await state.set_state(AdminStates.WAITING_CATEGORY_BUTTON_COLUMNS)

    await message.answer(
        "📐 نحوه نمایش دکمه این دسته‌بندی را انتخاب کنید:",
        reply_markup=button_columns_keyboard("admin:categories"),
    )


@router.callback_query(F.data.startswith("layout:columns:"))
async def handle_layout_columns(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return

    columns = int(callback.data.split(":")[2])

    if columns not in (1, 2):
        await callback.answer("❌ مقدار نامعتبر است.", show_alert=True)
        return

    current_state = await state.get_state()

    if current_state == AdminStates.WAITING_CATEGORY_BUTTON_COLUMNS.state:
        data = await state.get_data()

        async with get_session() as session:
            category = await CategoryService(session).create(
                data["category_name"],
                data.get("category_icon"),
                columns,
            )

        await state.clear()

        label = "تمام‌عرض" if columns == 1 else "دو ستونه"

        await callback.message.edit_text(
            f"✅ دسته‌بندی «{category.name}» ساخته شد.\n"
            f"📐 نمایش دکمه: {label}"
        )
        await callback.answer("ذخیره شد ✅")
        return

    if current_state == AdminStates.WAITING_PRODUCT_BUTTON_COLUMNS.state:
        data = await state.get_data()

        async with get_session() as session:
            product_service = ProductService(session)

            if data["product_type"] == "FIXED":
                product = await product_service.create_fixed(
                    data["category_id"],
                    data["product_name"],
                    data["fixed_price"],
                    columns,
                )
            else:
                product = await product_service.create_variable(
                    data["category_id"],
                    data["product_name"],
                    data["unit_price"],
                    data["min_qty"],
                    data["max_qty"],
                    columns,
                )

        await state.clear()

        label = "تمام‌عرض" if columns == 1 else "دو ستونه"

        await callback.message.edit_text(
            f"✅ محصول «{product.name}» ساخته شد.\n"
            f"📐 نمایش دکمه: {label}"
        )
        await callback.answer("ذخیره شد ✅")
        return

    await callback.answer("این انتخاب دیگر فعال نیست.", show_alert=True)


@router.callback_query(F.data.startswith("admin:category:del:"))
async def handle_admin_category_delete_ask(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        category = await CategoryService(session).get(category_id)
    if not category:
        await callback.answer("دسته‌بندی پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ آیا از حذف دسته‌بندی «{category.name}» مطمئن هستید؟\nاین کار قابل بازگشت نیست.",
        reply_markup=admin_category_delete_confirm_keyboard(category_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:category:delyes:"))
async def handle_admin_category_delete_confirm(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        try:
            await CategoryService(session).delete(category_id)
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return
        categories = await CategoryService(session).list_all()
    await callback.message.edit_text(
        "✅ دسته‌بندی حذف شد.\n\n📂 <b>دسته‌بندی‌ها</b>", reply_markup=admin_categories_keyboard(categories)
    )
    await callback.answer()


# ---------- عضویت اجباری ----------


@router.callback_query(F.data == "admin:channels")
async def handle_admin_channels(callback: CallbackQuery) -> None:
    async with get_session() as session:
        channels = await MembershipService(session).list_all_channels()
    if not channels:
        await callback.message.edit_text(
            "📢 <b>عضویت اجباری</b>\n\nهنوز کانالی ثبت نشده است.\nبرای شروع کانال را اضافه کنید.",
            reply_markup=admin_channels_keyboard([]),
        )
    else:
        await callback.message.edit_text(
            "📢 <b>کانال‌های اجباری</b>", reply_markup=admin_channels_keyboard(channels)
        )
    await callback.answer()


@router.callback_query(F.data == "admin:channel:add")
async def handle_admin_channel_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminStates.WAITING_CHANNEL_TITLE)
    await callback.message.edit_text(
        "➕ <b>افزودن کانال اجباری</b>\n\n"
        "1️⃣ نام نمایشی کانال را بفرستید.\n"
        "مثال: <code>Access Hub</code>",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.WAITING_CHANNEL_TITLE, F.text)
async def handle_channel_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if not title:
        await message.answer("❌ نام کانال نمی‌تواند خالی باشد.")
        return
    await state.update_data(channel_title=title[:128])
    await state.set_state(AdminStates.WAITING_CHANNEL_USERNAME)
    await message.answer(
        "2️⃣ یوزرنیم عمومی کانال را بفرستید، مثلاً <code>@AccessHubMarket</code>.\n"
        "اگر کانال Private است، Chat ID آن را بفرستید (مثلاً <code>-1001234567890</code>)."
    )


@router.message(AdminStates.WAITING_CHANNEL_USERNAME, F.text)
async def handle_channel_username(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    username = message.text.strip()
    if not username:
        await message.answer("❌ یوزرنیم/Chat ID نمی‌تواند خالی باشد.")
        return
    if not username.startswith("@") and not username.lstrip("-").isdigit():
        username = "@" + username
    try:
        chat = await message.bot.get_chat(username if username.startswith("@") else int(username))
        bot_member = await message.bot.get_chat_member(chat.id, message.bot.id)
        if bot_member.status not in {"administrator", "creator"}:
            await message.answer(
                "❌ ربات ادمین این کانال نیست.\n"
                "ابتدا ربات را در کانال Administrator کنید و دوباره تلاش کنید."
            )
            return
    except TelegramBadRequest:
        await message.answer(
            "❌ کانال پیدا نشد یا ربات به آن دسترسی ندارد.\n"
            "یوزرنیم/Chat ID را بررسی کنید و مطمئن شوید ربات ادمین کانال است."
        )
        return

    async with get_session() as session:
        exists = await session.scalar(
            select(RequiredChannel).where(RequiredChannel.username == username)
        )
        if exists:
            await state.clear()
            await message.answer("⚠️ این کانال قبلاً ثبت شده است.", reply_markup=admin_back_keyboard())
            return

    await state.update_data(channel_username=username)
    await state.set_state(AdminStates.WAITING_CHANNEL_INVITE_LINK)
    await message.answer(
        "3️⃣ لینک عضویت کانال را بفرستید.\n"
        "برای کانال عمومی می‌توانید <code>-</code> بفرستید تا لینک خودکار ساخته شود."
    )


@router.message(AdminStates.WAITING_CHANNEL_INVITE_LINK, F.text)
async def handle_channel_invite_link(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    invite = message.text.strip()
    invite = None if invite == "-" else invite
    if invite and not (invite.startswith("https://t.me/") or invite.startswith("http://t.me/")):
        await message.answer("❌ لینک باید به شکل https://t.me/... باشد یا برای صرف‌نظر کردن «-» بفرستید.")
        return

    async with get_session() as session:
        channel = await MembershipService(session).add_channel(
            title=data["channel_title"],
            username=data["channel_username"],
            invite_link=invite,
        )
        channels = await MembershipService(session).list_all_channels()

    await state.clear()
    await message.answer(
        f"✅ کانال «{channel.title}» با موفقیت اضافه شد.",
        reply_markup=admin_channels_keyboard(channels),
    )


@router.callback_query(F.data.startswith("admin:channel:toggle:"))
async def handle_admin_channel_toggle(callback: CallbackQuery) -> None:
    channel_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        await MembershipService(session).toggle_channel(channel_id)
        channels = await MembershipService(session).list_all_channels()
    await callback.message.edit_text(
        "📢 <b>کانال‌های اجباری</b>", reply_markup=admin_channels_keyboard(channels)
    )
    await callback.answer("ثبت شد ✅")


# ---------- تنظیمات ----------


@router.callback_query(F.data == "admin:settings")
async def handle_admin_settings(callback: CallbackQuery) -> None:
    async with get_session() as session:
        report_enabled = await SettingsService(session).is_order_report_enabled()
    await callback.message.edit_text(
        "⚙️ <b>تنظیمات</b>", reply_markup=admin_settings_keyboard(report_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:setting:toggle_report")
async def handle_admin_toggle_report(callback: CallbackQuery) -> None:
    async with get_session() as session:
        new_value = await SettingsService(session).toggle_order_report()
    await callback.message.edit_text(
        "⚙️ <b>تنظیمات</b>", reply_markup=admin_settings_keyboard(new_value)
    )
    await callback.answer("✅ ذخیره شد")


@router.callback_query(F.data.startswith("admin:setting:edit:"))
async def handle_admin_setting_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 3)[3]
    label = EDITABLE_SETTINGS.get(key, key)
    async with get_session() as session:
        current = await SettingsService(session).get(key)
        if key == "payment_info" and not current:
            card_number = await SettingsService(session).get("card_number") or ""
            card_holder = await SettingsService(session).get("card_holder_name") or ""
            description = await SettingsService(session).get("payment_description") or ""
            parts = []
            if card_number:
                parts.append(f"شماره کارت:\n{card_number}")
            if card_holder:
                parts.append(f"به نام:\n{card_holder}")
            if description:
                parts.append(f"توضیحات:\n{description}")
            current = "\n\n".join(parts)
    await state.set_state(AdminStates.WAITING_SETTING_VALUE)
    await state.update_data(setting_key=key)
    await callback.message.edit_text(
        f"⚙️ <b>{label}</b>\n\nمقدار فعلی:\n<code>{current or '—'}</code>\n\nمقدار جدید را بفرستید:",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


@router.message(AdminStates.WAITING_SETTING_VALUE, F.text)
async def handle_admin_setting_value(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data.get("setting_key")
    value = message.text.strip()

    if key == "token_transfer_fee_percent":
        try:
            fee = float(value)
        except ValueError:
            await message.answer("❗️ کارمزد باید عددی بین ۰ تا ۱۰۰ باشد.")
            return
        if not 0 <= fee <= 100:
            await message.answer("❗️ کارمزد باید بین ۰ تا ۱۰۰ درصد باشد.")
            return

    async with get_session() as session:
        await SettingsService(session).set(key, value)
    await state.clear()
    label = EDITABLE_SETTINGS.get(key, key)
    await message.answer(f"✅ «{label}» به‌روزرسانی شد.")


# ---------- شارژهای در انتظار ----------


@router.callback_query(F.data == "admin:deposits")
async def handle_admin_deposits(callback: CallbackQuery) -> None:
    async with get_session() as session:
        requests = await DepositService(session).list_pending()

    if not requests:
        await callback.message.edit_text("💳 درخواست در انتظاری نیست.", reply_markup=admin_back_keyboard())
        await callback.answer()
        return

    rows = [
        [
            InlineKeyboardButton(
                text=f"#{r.id} — {r.amount:,} تومان", callback_data=f"admin:deposit:view:{r.id}"
            )
        ]
        for r in requests
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    await callback.message.edit_text(
        "💳 <b>شارژهای در انتظار</b>\n\nبرای بررسی رسید و تأیید/رد، روی هر درخواست بزنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:deposit:view:"))
async def handle_admin_deposit_view(callback: CallbackQuery) -> None:
    """
    رسید یک درخواست شارژ را همراه دکمه‌ی تأیید/رد نمایش می‌دهد. این همان
    دکمه‌هایی است که موقع ارسال رسید هم مستقیم برای ادمین ارسال می‌شود؛
    اینجا یک راه دوم برای دسترسی به آن‌هاست، برای وقتی پیام اصلی از دست رفته.
    """
    request_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        request = await DepositService(session).get(request_id)
        target_user = await session.get(User, request.user_id) if request else None

    if not request:
        await callback.answer("درخواست پیدا نشد.", show_alert=True)
        return
    if request.status != DepositRequestStatus.PENDING.value:
        await callback.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
        return

    username = f"@{target_user.username}" if target_user and target_user.username else "—"
    tg_id = target_user.telegram_id if target_user else "—"
    caption = (
        "💰 <b>درخواست شارژ کیف پول</b>\n\n"
        f"کاربر: {username}\n"
        f"Telegram ID: <code>{tg_id}</code>\n\n"
        f"مبلغ: <b>{request.amount:,} تومان</b>\n"
        f"شماره درخواست: #{request.id}"
    )
    await callback.answer()
    if request.receipt_file_id:
        await callback.message.answer_photo(
            photo=request.receipt_file_id,
            caption=caption,
            reply_markup=admin_deposit_decision_keyboard(request.id),
        )
    else:
        await callback.message.answer(
            caption + "\n\n⚠️ رسیدی برای این درخواست ثبت نشده.",
            reply_markup=admin_deposit_decision_keyboard(request.id),
        )


# ---------- سفارش‌های در انتظار ----------


@router.callback_query(F.data == "admin:orders")
async def handle_admin_orders(callback: CallbackQuery) -> None:
    async with get_session() as session:
        rows = await session.execute(
            select(Order).where(Order.status == OrderStatus.WAITING_ADMIN.value).order_by(Order.created_at)
        )
        orders = list(rows.scalars().all())
        lines = []
        for order in orders:
            product = await session.get(Product, order.product_id)
            lines.append(
                f"#{order.order_number} — {product.name if product else '—'} — {order.final_price:,} تومان"
            )

    if not orders:
        await callback.message.edit_text("📦 سفارش در انتظاری نیست.", reply_markup=admin_back_keyboard())
    else:
        text = "📦 <b>سفارش‌های در انتظار تحویل</b>\n\n" + "\n".join(lines)
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    await callback.answer()
