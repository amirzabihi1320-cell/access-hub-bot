"""
مدیریت پنل‌های VPN از پنل ادمین (بند ۳۴ سند) - بدون هیچ نیازی به تغییر
Source Code برای افزودن/ویرایش/حذف یک پنل.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.enums import HealthStatus, VPNPanelStatus
from app.models.vpn_panel import VPNPanel
from app.models.vpn_service import VPNService
from app.providers.exceptions import ProviderError
from app.providers.registry import build_vpn_provider
from app.providers.vpn.base import BaseVPNProvider


class VPNPanelService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[VPNPanel]:
        result = await self.session.execute(select(VPNPanel).order_by(VPNPanel.priority, VPNPanel.id))
        return list(result.scalars().all())

    async def list_active_sorted(self) -> list[VPNPanel]:
        """برای Smart Panel Selection: فقط پنل‌های فعال، به ترتیب اولویت."""
        result = await self.session.execute(
            select(VPNPanel)
            .where(VPNPanel.status == VPNPanelStatus.ACTIVE.value)
            .order_by(VPNPanel.priority, VPNPanel.id)
        )
        return list(result.scalars().all())

    async def get(self, panel_id: int) -> VPNPanel | None:
        result = await self.session.execute(select(VPNPanel).where(VPNPanel.id == panel_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        panel_type: str,
        base_url: str,
        username: str,
        password: str,
        priority: int = 100,
        default_inbound_id: int | None = None,
    ) -> VPNPanel:
        panel = VPNPanel(
            name=name.strip()[:128],
            panel_type=panel_type,
            base_url=base_url.strip().rstrip("/"),
            username=username.strip(),
            password_encrypted=encrypt_secret(password),
            priority=priority,
            default_inbound_id=default_inbound_id,
        )
        self.session.add(panel)
        await self.session.commit()
        return panel

    async def delete(self, panel_id: int) -> None:
        panel = await self.get(panel_id)
        if panel is None:
            raise ValueError("پنل پیدا نشد.")
        has_services = await self.session.scalar(
            select(VPNService.id).where(VPNService.panel_id == panel_id).limit(1)
        )
        if has_services:
            raise ValueError(
                "این پنل سرویس فعال ثبت‌شده دارد؛ به‌جای حذف، آن را غیرفعال کن "
                "تا سرویس‌های موجود قابل مدیریت/تمدید بمانند."
            )
        await self.session.delete(panel)
        await self.session.commit()

    async def toggle_status(self, panel_id: int) -> VPNPanel:
        panel = await self.get(panel_id)
        if panel is None:
            raise ValueError("پنل پیدا نشد.")
        panel.status = (
            VPNPanelStatus.DISABLED.value
            if panel.status == VPNPanelStatus.ACTIVE.value
            else VPNPanelStatus.ACTIVE.value
        )
        await self.session.commit()
        return panel

    def build_provider(self, panel: VPNPanel) -> BaseVPNProvider:
        """نمونه‌ی Provider آماده با Credential رمزگشایی‌شده می‌سازد."""
        return build_vpn_provider(
            panel.panel_type,
            base_url=panel.base_url,
            username=panel.username,
            password=decrypt_secret(panel.password_encrypted),
            default_inbound_id=panel.default_inbound_id,
        )

    async def test_connection(self, panel_id: int) -> tuple[bool, str]:
        """
        اتصال واقعی به پنل را تست می‌کند (بند ۳۴: Test Connection) و
        نتیجه را روی خودِ پنل هم کش می‌کند تا Smart Panel Selection از
        زدن درخواست تکراری بی‌نیاز شود.
        """
        panel = await self.get(panel_id)
        if panel is None:
            raise ValueError("پنل پیدا نشد.")

        provider = self.build_provider(panel)
        try:
            health = await provider.health_check()
        except ProviderError as exc:
            panel.last_health_status = HealthStatus.OFFLINE.value
            panel.last_health_detail = exc.message
            panel.last_health_checked_at = datetime.now(timezone.utc)
            await self.session.commit()
            return False, exc.message
        finally:
            await provider.close()

        panel.last_health_status = health.status.value
        panel.last_health_detail = health.detail
        panel.last_health_checked_at = datetime.now(timezone.utc)
        await self.session.commit()

        ok = health.status == HealthStatus.ONLINE
        return ok, health.detail
