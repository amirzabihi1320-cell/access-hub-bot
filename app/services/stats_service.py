"""
سرویس آمار/داشبورد فروش برای پنل ادمین (بخش ۲۸ سند اصلی: Admin Dashboard).
همه‌ی محاسبات فقط Read-Only هستند و روی جدول‌های موجود Order/User اجرا
می‌شوند؛ هیچ جدول جدیدی لازم نیست.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus
from app.models.order import Order
from app.models.product import Product
from app.models.user import User

_PAID_STATUSES = [OrderStatus.WAITING_ADMIN.value, OrderStatus.COMPLETED.value]


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _revenue_since(self, since: datetime | None) -> tuple[int, int]:
        """(مجموع تومان, تعداد سفارش) از یک تاریخ به بعد؛ None یعنی کل تاریخچه."""
        query = select(func.coalesce(func.sum(Order.final_price), 0), func.count()).where(
            Order.status.in_(_PAID_STATUSES)
        )
        if since is not None:
            query = query.where(Order.created_at >= since)
        result = await self.session.execute(query)
        total, count = result.one()
        return total, count

    async def sales_summary(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        today_rev, today_count = await self._revenue_since(today_start)
        week_rev, week_count = await self._revenue_since(week_start)
        month_rev, month_count = await self._revenue_since(month_start)
        all_rev, all_count = await self._revenue_since(None)

        return {
            "today": {"revenue": today_rev, "orders": today_count},
            "week": {"revenue": week_rev, "orders": week_count},
            "month": {"revenue": month_rev, "orders": month_count},
            "all_time": {"revenue": all_rev, "orders": all_count},
        }

    async def top_products(self, limit: int = 5, days: int | None = 30) -> list[tuple[str, int, int]]:
        """پرفروش‌ترین محصولات: (نام, تعداد سفارش, مجموع فروش تومان)."""
        query = (
            select(Product.name, func.count(Order.id), func.coalesce(func.sum(Order.final_price), 0))
            .join(Order, Order.product_id == Product.id)
            .where(Order.status.in_(_PAID_STATUSES))
        )
        if days is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.where(Order.created_at >= since)
        query = query.group_by(Product.id, Product.name).order_by(func.count(Order.id).desc()).limit(limit)

        result = await self.session.execute(query)
        return [(name, count, revenue) for name, count, revenue in result.all()]

    async def user_stats(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        total_result = await self.session.execute(select(func.count()).select_from(User))
        total_users = total_result.scalar_one()

        new_today_result = await self.session.execute(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        )
        new_today = new_today_result.scalar_one()

        active_week_result = await self.session.execute(
            select(func.count()).select_from(User).where(User.last_activity >= week_start)
        )
        active_week = active_week_result.scalar_one()

        return {"total": total_users, "new_today": new_today, "active_week": active_week}
