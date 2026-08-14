from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.orders import admin_order_deliver_keyboard
from app.bot.keyboards.shop import categories_keyboard, product_detail_keyboard, products_keyboard
from app.bot.states.shop_states import ProductQuantityStates
from app.config.settings import get_settings
from app.database.base import get_session
from app.services.category_service import CategoryService
from app.services.order_service import OrderService, ProductUnavailableError, build_order_report_text
from app.services.pricing_service import InvalidQuantityError, calculate_price
from app.services.product_service import ProductService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.services.wallet_service import InsufficientBalanceError
from app.utils.keyboards import clamp_columns
from app.utils.message_manager import MessageManager

router = Router(name="shop")
settings = get_settings()

# قفل درون‌حافظه‌ای برای جلوگیری از دوبار کلیک روی پرداخت قبل از تمام‌شدن
# پردازش قبلی (بخش ۱۷: جلوگیری از Duplicate Order). چون سرویس روی Render
# تک‌پردازه اجرا می‌شود، این سطح از محافظت برای این فاز کافی است.
_processing_purchases: set[int] = set()


async def build_categories_view(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup] | None:
    """خروجی مشترک بین ورودی اولیه (از منوی ثابت) و ناوبری داخلی (دکمه بازگشت)."""
    categories = await CategoryService(session).list_active()
    if not categories:
        return None
    columns = clamp_columns(await SettingsService(session).get("shop_buttons_per_row"))
    return "🛍 دسته‌بندی‌ها", categories_keyboard(categories, columns)


@router.callback_query(F.data == "menu:shop")
async def handle_shop_back(callback: CallbackQuery) -> None:
    async with get_session() as session:
        view = await build_categories_view(session)

    if not view:
        await callback.answer("فعلاً محصولی ثبت نشده.", show_alert=True)
        return

    text, keyboard = view
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("shop:category:"))
async def handle_category(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[2])

    async with get_session() as session:
        products = await ProductService(session).list_by_category(category_id)
        category = await CategoryService(session).get(category_id)
        columns = clamp_columns(await SettingsService(session).get("shop_buttons_per_row"))

    if not products:
        await callback.answer("محصولی در این دسته‌بندی نیست.", show_alert=True)
        return

    title = category.name if category else "محصولات"
    await callback.message.edit_text(
        f"📂 {title}:", reply_markup=products_keyboard(products, category_id, columns)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("shop:product:"))
async def handle_product_detail(callback: CallbackQuery) -> None:
    product_id = int(callback.data.split(":")[2])

    async with get_session() as session:
        product = await ProductService(session).get(product_id)

    if not product:
        await callback.answer("محصول پیدا نشد.", show_alert=True)
        return

    text = f"🧾 <b>{product.name}</b>\n\n"
    if product.description:
        text += f"{product.description}\n\n"

    if product.product_type == "FIXED":
        text += f"قیمت:\n<b>{product.fixed_price:,} تومان</b>"
    else:
        text += (
            f"قیمت هر واحد: <b>{product.unit_price:,} تومان</b>\n"
            f"حداقل: {product.min_quantity or 1} | حداکثر: {product.max_quantity or '∞'}"
        )

    await callback.message.edit_text(text, reply_markup=product_detail_keyboard(product))
    await callback.answer()


@router.callback_query(F.data.startswith("shop:enter_qty:"))
async def handle_enter_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    product_id = int(callback.data.split(":")[2])
    # آیدی همین پیام را نگه می‌داریم تا بعد از دریافت تعداد، هم این پیام و
    # هم عددی که کاربر تایپ می‌کند پاک شوند و چت شلوغ نشود (بخش ۴ سند).
    await state.update_data(product_id=product_id, qty_prompt_message_id=callback.message.message_id)
    await state.set_state(ProductQuantityStates.WAITING_QUANTITY)

    await callback.message.edit_text("🔢 تعداد را وارد کنید:")
    await callback.answer()


@router.message(ProductQuantityStates.WAITING_QUANTITY)
async def handle_quantity_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data["product_id"]
    manager = MessageManager(message.bot, message.chat.id, state)

    if not message.text or not message.text.strip().isdigit():
        await manager.delete_message_id(message.message_id)
        return

    quantity = int(message.text.strip())

    async with get_session() as session:
        product = await ProductService(session).get(product_id)

    if not product:
        await manager.delete_message_id(message.message_id)
        prompt_id = data.get("qty_prompt_message_id")
        if prompt_id:
            await manager.delete_message_id(prompt_id)
        await state.clear()
        await manager.send("❌ محصول پیدا نشد.")
        return

    try:
        result = calculate_price(product, quantity)
    except InvalidQuantityError as e:
        await manager.delete_message_id(message.message_id)
        await message.answer(f"❌ {e}")
        return

    # پیام پرامپت «تعداد را وارد کنید» و پیامی که کاربر تایپ کرده هر دو پاک می‌شوند.
    prompt_id = data.get("qty_prompt_message_id")
    if prompt_id:
        await manager.delete_message_id(prompt_id)
    await manager.delete_message_id(message.message_id)

    await state.update_data(qty_prompt_message_id=None)
    await state.set_state(None)

    text = (
        f"🧾 <b>سفارش شما</b>\n\n"
        f"{product.name} — {result.quantity} عدد\n\n"
        f"قیمت نهایی:\n<b>{result.total_price:,} تومان</b>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ پرداخت با کیف پول",
                callback_data=f"shop:buy:{product.id}:{result.quantity}",
            )],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"shop:category:{product.category_id}")],
        ]
    )
    await manager.send(text, reply_markup=keyboard)
    await state.clear()


@router.callback_query(F.data.startswith("shop:buy:"))
async def handle_buy(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    if user_id in _processing_purchases:
        await callback.answer("⏳ درخواست قبلی در حال پردازش است.", show_alert=True)
        return

    _processing_purchases.add(user_id)
    try:
        parts = callback.data.split(":")
        product_id, quantity = int(parts[2]), int(parts[3])

        async with get_session() as session:
            user = await UserService(session).get_or_create(
                user_id, callback.from_user.username, callback.from_user.first_name,
                callback.from_user.last_name,
            )
            product = await ProductService(session).get(product_id)
            order_service = OrderService(session)
            try:
                order = await order_service.create_and_pay(user.id, product_id, quantity)
            except InsufficientBalanceError:
                await callback.answer("❌ موجودی کیف پول کافی نیست.", show_alert=True)
                return
            except (ProductUnavailableError, InvalidQuantityError, ValueError) as e:
                await callback.answer(f"❌ {e}", show_alert=True)
                return

        await callback.message.edit_text(
            f"✅ <b>پرداخت موفق</b>\n\n"
            f"{product.name} — {order.final_price:,} تومان\n"
            f"شماره سفارش: #{order.order_number}\n\n"
            "سفارش شما برای آماده‌سازی ارسال شد.",
        )
        await callback.answer()
        # این پیام حالا حاوی «رسید تأیید سفارش» است (دسته PAYMENT/ORDER در بخش ۴
        # سند) و نباید هرگز خودکار پاک شود؛ پس آن را از ردیابی پیام‌های موقت
        # خارج می‌کنیم تا با پاکسازی مرحله‌ی بعد از بین نرود.
        await state.update_data(temp_message_ids=[])

        # اطلاع به ادمین‌ها برای تحویل دستی (بخش ۱۸) + گزارش به کانال (بخش ۳۳)
        username = f"@{callback.from_user.username}" if callback.from_user.username else "—"
        admin_text = (
            "🛍 <b>سفارش جدید</b>\n\n"
            f"کاربر: {username}\n"
            f"محصول: {product.name}\n"
            f"تعداد: {order.quantity}\n"
            f"مبلغ: {order.final_price:,} تومان\n"
            f"سفارش: #{order.order_number}"
        )
        for admin_id in settings.admin_ids:
            try:
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=admin_order_deliver_keyboard(order.id),
                )
            except Exception:
                continue

        try:
            async with get_session() as session:
                report_enabled = await SettingsService(session).is_order_report_enabled()
        except Exception:
            report_enabled = True

        if report_enabled:
            try:
                await callback.bot.send_message(
                    chat_id=settings.report_channel_id,
                    text=build_order_report_text(order, product.name),
                )
            except Exception:
                pass
    finally:
        _processing_purchases.discard(user_id)
