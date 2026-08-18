"""
فاز ۴: سفارش‌ها + پرداخت با کیف پول + تحویل (بخش ۱۵-۱۹ سند).

create_and_pay در یک واحد کاری اتمیک انجام می‌شود: ساخت سفارش → کسر از
کیف پول (که خودش Ledger ثبت می‌کند) → تغییر وضعیت. اگر موجودی کافی نباشد،
InsufficientBalanceError از WalletService بالا می‌آید و کل تراکنش (شامل
ساخت سفارش) توسط get_session() rollback می‌شود؛ یعنی سفارش نیمه‌کاره
باقی نمی‌ماند.

چون هنوز Inventory/Provider API (فاز آینده) پیاده نشده، تحویل همیشه MANUAL
است: سفارش در وضعیت WAITING_ADMIN می‌ماند تا ادمین با دکمه «تحویل شد»
آن را COMPLETED کند.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus, WalletTransactionType
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.pricing_service import calculate_price
from app.services.settings_service import SettingsService
from app.services.wallet_service import WalletService

class OrderAlreadyProcessedError(Exception):
    """این سفارش قبلاً تحویل داده شده یا در وضعیت دیگری است."""


class ProductUnavailableError(Exception):
    """محصول حذف/غیرفعال شده است."""


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_and_pay(self, user_id: int, product_id: int, quantity: int) -> Order:
        product = await self.session.get(Product, product_id)
        if not product or not product.status:
            raise ProductUnavailableError("این محصول در دسترس نیست.")

        # بررسی مجدد قیمت/تعداد درست قبل از برداشت پول (بخش ۱۶)
        price = calculate_price(product, quantity)

        order = Order(
            user_id=user_id,
            product_id=product_id,
            quantity=price.quantity,
            unit_price=price.unit_price,
            final_price=price.total_price,
            status=OrderStatus.PENDING.value,
            delivery_type="MANUAL",
        )
        self.session.add(order)
        await self.session.flush()  # برای گرفتن order.id قبل از commit
        order.order_number = f"AH-{order.id:06d}"

        # اگر موجودی کافی نباشد، اینجا Exception بالا می‌رود و کل session
        # (شامل ساخت سفارش بالا) توسط get_session() rollback می‌شود.
        await WalletService(self.session).debit(
            user_id=user_id,
            amount=price.total_price,
            type_=WalletTransactionType.PURCHASE,
            reference_id=f"order:{order.id}",
            description=f"خرید {product.name}",
        )

        order.status = OrderStatus.WAITING_ADMIN.value

        user = await self.session.get(User, user_id)
        user.total_purchases += 1
        user.total_spent += price.total_price

        # پاداش رفرال (Cashback): اگر خریدار توسط کاربر دیگری معرفی شده و
        # درصد پاداش در تنظیمات فعال باشد، درصدی از مبلغ همین خرید به
        # کیف‌پول معرف واریز می‌شود. چون هر فراخوانی create_and_pay یک
        # سفارش کاملاً جدید (order.id تازه) می‌سازد، reference_id ذاتاً
        # یکتاست و امکان واریز تکراری برای یک خرید وجود ندارد.
        if user.referred_by:
            cashback_percent_raw = await SettingsService(self.session).get("referral_cashback_percent", "0")
            try:
                cashback_percent = int(cashback_percent_raw)
            except (TypeError, ValueError):
                cashback_percent = 0
            if cashback_percent > 0:
                cashback_amount = price.total_price * cashback_percent // 100
                if cashback_amount > 0:
                    referrer = await self.session.get(User, user.referred_by)
                    if referrer:
                        await WalletService(self.session).credit(
                            user_id=referrer.id,
                            amount=cashback_amount,
                            type_=WalletTransactionType.BONUS,
                            reference_id=f"referral-cashback:order:{order.id}",
                            description=f"پاداش رفرال از خرید {product.name}",
                        )

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get(self, order_id: int) -> Order | None:
        result = await self.session.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def _get_locked(self, order_id: int) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def mark_delivered(self, order_id: int) -> Order:
        order = await self._get_locked(order_id)
        if order is None:
            raise ValueError("سفارش پیدا نشد.")
        if order.status != OrderStatus.WAITING_ADMIN.value:
            raise OrderAlreadyProcessedError("این سفارش قبلاً پردازش شده است.")
        order.status = OrderStatus.COMPLETED.value
        await self.session.commit()
        return order

    async def list_for_user(self, user_id: int, limit: int = 10) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ---------- ادمین (بخش ۲۸: Dashboard) ----------

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Order))
        return result.scalar_one()

    async def count_pending(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.WAITING_ADMIN.value)
        )
        return result.scalar_one()

    async def total_revenue(self) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Order.final_price), 0)).where(
                Order.status.in_([OrderStatus.WAITING_ADMIN.value, OrderStatus.COMPLETED.value])
            )
        )
        return result.scalar_one()

    async def stats_since(self, since) -> tuple[int, int]:
        """(تعداد سفارش, مجموع مبلغ) برای سفارش‌های موفق از یک تاریخ به بعد."""
        result = await self.session.execute(
            select(func.count(), func.coalesce(func.sum(Order.final_price), 0))
            .where(
                Order.status.in_([OrderStatus.WAITING_ADMIN.value, OrderStatus.COMPLETED.value]),
                Order.created_at >= since,
            )
        )
        row = result.one()
        return row[0], row[1]

    async def best_sellers(self, limit: int = 5, since=None) -> list[tuple[int, int, int]]:
        """(product_id, تعداد فروش, مجموع مبلغ) برای پرفروش‌ترین محصولات."""
        query = (
            select(Order.product_id, func.count(), func.coalesce(func.sum(Order.final_price), 0))
            .where(Order.status.in_([OrderStatus.WAITING_ADMIN.value, OrderStatus.COMPLETED.value]))
            .group_by(Order.product_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        if since is not None:
            query = query.where(Order.created_at >= since)
        result = await self.session.execute(query)
        return [(row[0], row[1], row[2]) for row in result.all()]

    async def pending_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.WAITING_ADMIN.value)
        )
        return result.scalar_one()


def build_order_report_text(order: Order, product_name: str) -> str:
    """
    متن گزارش خلاصه‌ی سفارش برای کانال گزارش‌ها (بخش ۳۳ سند).
    عمداً هیچ اطلاعات حساسی (شماره تلفن، شماره کارت، آیدی عددی کاربر،
    یوزرنیم و ...) در این متن قرار نمی‌گیرد.
    """
    status_labels = {
        OrderStatus.WAITING_ADMIN.value: "🕐 در انتظار تحویل",
        OrderStatus.COMPLETED.value: "✅ تکمیل شد",
        OrderStatus.PAID.value: "✅ پرداخت شد",
    }
    status_text = status_labels.get(order.status, order.status)
    return (
        "🛍 <b>سفارش جدید</b>\n\n"
        f"محصول:\n{product_name}\n\n"
        f"تعداد: {order.quantity}\n"
        f"مبلغ: {order.final_price:,} تومان\n\n"
        f"Order:\n#{order.order_number}\n\n"
        f"وضعیت:\n{status_text}"
    )
