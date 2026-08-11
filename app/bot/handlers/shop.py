from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.keyboards.shop import categories_keyboard, product_detail_keyboard, products_keyboard
from app.bot.states.shop_states import ProductQuantityStates
from app.database.base import get_session
from app.services.category_service import CategoryService
from app.services.pricing_service import InvalidQuantityError, calculate_price
from app.services.product_service import ProductService

router = Router(name="shop")


@router.callback_query(F.data == "menu:home")
async def handle_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🌐 <b>Access Hub</b>\n\nخوش آمدید به Access Hub.\nدسترسی آسان به سرویس‌ها و محصولات دیجیتال.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:shop")
async def handle_shop(callback: CallbackQuery) -> None:
    async with get_session() as session:
        categories = await CategoryService(session).list_active()

    if not categories:
        await callback.answer("فعلاً محصولی ثبت نشده.", show_alert=True)
        return

    await callback.message.edit_text("🛍 دسته‌بندی‌ها را انتخاب کنید:", reply_markup=categories_keyboard(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("shop:category:"))
async def handle_category(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[2])

    async with get_session() as session:
        products = await ProductService(session).list_by_category(category_id)
        category = await CategoryService(session).get(category_id)

    if not products:
        await callback.answer("محصولی در این دسته‌بندی نیست.", show_alert=True)
        return

    title = category.name if category else "محصولات"
    await callback.message.edit_text(f"📂 {title}:", reply_markup=products_keyboard(products, category_id))
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
    await state.update_data(product_id=product_id)
    await state.set_state(ProductQuantityStates.WAITING_QUANTITY)

    await callback.message.edit_text("🔢 تعداد مورد نظر را وارد کنید:")
    await callback.answer()


@router.message(ProductQuantityStates.WAITING_QUANTITY)
async def handle_quantity_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data["product_id"]

    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ لطفاً فقط عدد وارد کنید.")
        return

    quantity = int(message.text.strip())

    async with get_session() as session:
        product = await ProductService(session).get(product_id)

    if not product:
        await message.answer("❌ محصول پیدا نشد.")
        await state.clear()
        return

    try:
        result = calculate_price(product, quantity)
    except InvalidQuantityError as e:
        await message.answer(f"❌ {e}")
        return

    await state.clear()

    text = (
        f"🧾 <b>سفارش شما</b>\n\n"
        f"{product.name} — {result.quantity} عدد\n\n"
        f"قیمت نهایی:\n<b>{result.total_price:,} تومان</b>"
    )
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ پرداخت با کیف پول",
                callback_data=f"shop:buy:{product.id}:{result.quantity}",
            )],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"shop:category:{product.category_id}")],
        ]
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("shop:buy:"))
async def handle_buy_placeholder(callback: CallbackQuery) -> None:
    # پرداخت واقعی با کیف پول در فاز ۳/۴ پیاده‌سازی می‌شود.
    await callback.answer(
        "💰 سیستم پرداخت با کیف پول در فاز بعدی فعال می‌شود.", show_alert=True
    )
