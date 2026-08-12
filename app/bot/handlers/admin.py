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
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.admin import (
    EDITABLE_SETTINGS,
    admin_back_keyboard,
    admin_categories_keyboard,
    admin_channels_keyboard,
    admin_dashboard_keyboard,
    admin_product_category_pick_keyboard,
    admin_product_detail_keyboard,
    admin_product_type_pick_keyboard,
    admin_products_keyboard,
    admin_settings_keyboard,
)
from app.bot.states.admin_states import AdminStates
from app.config.settings import get_settings
from app.core.enums import OrderStatus
from app.database.base import get_session
from app.models.order import Order
from app.models.product import Product
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

    data = await state.get_data()
    async with get_session() as session:
        product = await ProductService(session).create_fixed(data["category_id"], data["product_name"], price)
    await state.clear()
    await message.answer(f"✅ محصول «{product.name}» با قیمت {price:,} تومان ساخته شد.")


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

    async with get_session() as session:
        product = await ProductService(session).create_variable(
            data["category_id"], data["product_name"], data["unit_price"], data["min_qty"], max_qty
        )
    await state.clear()
    await message.answer(
        f"✅ محصول «{product.name}» ساخته شد.\nقیمت واحد: {data['unit_price']:,} تومان\n"
        f"محدوده: {data['min_qty']} تا {max_qty}"
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
    data = await state.get_data()
    icon = None if message.text.strip() == "-" else message.text.strip()
    async with get_session() as session:
        category = await CategoryService(session).create(data["category_name"], icon)
    await state.clear()
    await message.answer(f"✅ دسته‌بندی «{category.name}» ساخته شد.")


# ---------- عضویت اجباری ----------


@router.callback_query(F.data == "admin:channels")
async def handle_admin_channels(callback: CallbackQuery) -> None:
    async with get_session() as session:
        channels = await MembershipService(session).list_all_channels()
    if not channels:
        await callback.message.edit_text("📢 کانالی ثبت نشده.", reply_markup=admin_back_keyboard())
    else:
        await callback.message.edit_text(
            "📢 <b>کانال‌های اجباری</b>", reply_markup=admin_channels_keyboard(channels)
        )
    await callback.answer()


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
    await callback.message.edit_text("⚙️ <b>تنظیمات</b>", reply_markup=admin_settings_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:setting:edit:"))
async def handle_admin_setting_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 3)[3]
    label = EDITABLE_SETTINGS.get(key, key)
    async with get_session() as session:
        current = await SettingsService(session).get(key, "")
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
    async with get_session() as session:
        await SettingsService(session).set(key, message.text.strip())
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

    text = "💳 <b>شارژهای در انتظار</b>\n\n" + "\n".join(
        f"#{r.id} — {r.amount:,} تومان" for r in requests
    )
    await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
    await callback.answer()


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
