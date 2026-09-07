"""
مدیریت تنظیمات Payment Providerها (Tronado و آینده) از پنل ادمین -
دقیقاً هم‌الگو با VPNPanelService، بند ۲ و ۲۰ سند ماژول اضافه.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.enums import HealthStatus, PaymentProviderStatus
from app.models.payment_provider_config import PaymentProviderConfig
from app.providers.exceptions import ProviderError
from app.providers.payment.base import BasePaymentProvider
from app.providers.payment.tronado import ProviderNotConfiguredError
from app.providers.registry import PAYMENT_PROVIDERS, build_payment_provider


class PaymentProviderConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[PaymentProviderConfig]:
        result = await self.session.execute(select(PaymentProviderConfig).order_by(PaymentProviderConfig.id))
        return list(result.scalars().all())

    async def list_unconfigured_types(self) -> list[str]:
        """نوع‌های Payment Provider که در registry هستند ولی هنوز در DB تنظیم نشده‌اند."""
        configured = {c.provider_type for c in await self.list_all()}
        return [t for t in PAYMENT_PROVIDERS.keys() if t not in configured]

    async def get(self, config_id: int) -> PaymentProviderConfig | None:
        result = await self.session.execute(select(PaymentProviderConfig).where(PaymentProviderConfig.id == config_id))
        return result.scalar_one_or_none()

    async def get_by_type(self, provider_type: str) -> PaymentProviderConfig | None:
        result = await self.session.execute(
            select(PaymentProviderConfig).where(PaymentProviderConfig.provider_type == provider_type)
        )
        return result.scalar_one_or_none()

    async def create(self, *, provider_type: str, api_url: str, api_key: str) -> PaymentProviderConfig:
        existing = await self.get_by_type(provider_type)
        if existing is not None:
            raise ValueError(f"برای «{provider_type}» قبلاً تنظیمات ثبت شده است.")
        config = PaymentProviderConfig(
            provider_type=provider_type,
            api_url=api_url.strip().rstrip("/"),
            api_key_encrypted=encrypt_secret(api_key.strip()),
            status=PaymentProviderStatus.DISABLED.value,
        )
        self.session.add(config)
        await self.session.commit()
        return config

    async def update_credentials(self, config_id: int, *, api_url: str | None = None, api_key: str | None = None) -> PaymentProviderConfig:
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")
        if api_url is not None:
            config.api_url = api_url.strip().rstrip("/")
        if api_key is not None:
            config.api_key_encrypted = encrypt_secret(api_key.strip())
        await self.session.commit()
        return config

    async def set_webhook_url(self, config_id: int, webhook_url: str) -> PaymentProviderConfig:
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")
        config.webhook_url = webhook_url.strip()
        await self.session.commit()
        return config

    async def toggle_status(self, config_id: int) -> PaymentProviderConfig:
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")
        config.status = (
            PaymentProviderStatus.DISABLED.value
            if config.status == PaymentProviderStatus.ACTIVE.value
            else PaymentProviderStatus.ACTIVE.value
        )
        await self.session.commit()
        return config

    async def toggle_auto_verify(self, config_id: int) -> PaymentProviderConfig:
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")
        config.auto_verify = not config.auto_verify
        await self.session.commit()
        return config

    async def delete(self, config_id: int) -> None:
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")
        await self.session.delete(config)
        await self.session.commit()

    def build_provider(self, config: PaymentProviderConfig) -> BasePaymentProvider:
        return build_payment_provider(
            config.provider_type,
            api_key=decrypt_secret(config.api_key_encrypted or ""),
            api_url=config.api_url or "",
        )

    async def test_connection(self, config_id: int) -> tuple[bool, str]:
        """
        همون الگوی VPNPanelService.test_connection - با یک تفاوت: تا وقتی
        TronadoProvider واقعی پیاده نشده (بند ۲۵ سند)، ProviderNotConfiguredError
        را هم به‌عنوان یک نتیجه‌ی مشخص (نه Crash) مدیریت می‌کند.
        """
        config = await self.get(config_id)
        if config is None:
            raise ValueError("تنظیمات پیدا نشد.")

        provider = self.build_provider(config)
        try:
            health = await provider.health_check()
        except ProviderNotConfiguredError as exc:
            detail = str(exc)
            config.last_health_status = HealthStatus.UNKNOWN.value
            config.last_health_detail = detail
            config.last_health_checked_at = datetime.now(timezone.utc)
            await self.session.commit()
            return False, detail
        except ProviderError as exc:
            config.last_health_status = HealthStatus.OFFLINE.value
            config.last_health_detail = exc.message
            config.last_health_checked_at = datetime.now(timezone.utc)
            await self.session.commit()
            return False, exc.message
        finally:
            await provider.close()

        config.last_health_status = health.status.value
        config.last_health_detail = health.detail
        config.last_health_checked_at = datetime.now(timezone.utc)
        await self.session.commit()

        ok = health.status == HealthStatus.ONLINE
        return ok, health.detail
