"""
هماهنگ‌کننده‌ی فلوی واریز TRX (بند ۴ سند): از انتخاب کاربر تا Credit
نهایی کیف‌پول. این سرویس هیچ Endpoint خاصی از Tronado را مستقیم صدا
نمی‌زند - همیشه از طریق app.providers.registry.build_payment_provider
(که BasePaymentProvider برمی‌گرداند) کار می‌کند، تا Core به Tronado
وابسته نباشد (بند ۲۴ سند: Modularity).

⚠️ تا وقتی TronadoProvider واقعی پیاده نشده (به app/providers/payment/tronado.py
نگاه کن)، create_deposit_order/verify اینجا خطای ProviderNotConfiguredError
همان Provider را عبور می‌دهند - عمداً کنترل نشده، چون handler بالادستی
باید پیام روشن "این روش پرداخت هنوز فعال نیست" به کاربر نشان دهد، نه
پیام گنگ.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.core.enums import (
    CryptoCurrency,
    CryptoDepositStatus,
    CryptoWalletTxType,
    PaymentProviderStatus,
    PaymentProviderType,
)
from app.models.crypto_deposit import CryptoDepositOrder
from app.models.payment_provider_config import PaymentProviderConfig
from app.providers.registry import build_payment_provider
from app.services.crypto_wallet_service import CryptoWalletService

_QUOTE_EXPIRY_SECONDS = 60 * 15  # بند ۴: کاربر باید مهلت معقولی برای پرداخت داشته باشد.


class PaymentProviderDisabledError(Exception):
    """این روش پرداخت فعلاً توسط ادمین غیرفعال یا پیکربندی نشده است."""


class DepositOrderNotFoundError(Exception):
    pass


class CryptoDepositService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_active_config(self, provider_type: PaymentProviderType) -> PaymentProviderConfig:
        result = await self.session.execute(
            select(PaymentProviderConfig).where(PaymentProviderConfig.provider_type == provider_type.value)
        )
        config = result.scalar_one_or_none()
        if config is None or config.status != PaymentProviderStatus.ACTIVE.value:
            raise PaymentProviderDisabledError(
                f"روش پرداخت {provider_type.value} توسط ادمین فعال نشده است."
            )
        return config

    async def create_deposit_request(
        self,
        user_id: int,
        toman_amount: int,
        provider_type: PaymentProviderType = PaymentProviderType.TRONADO,
    ) -> CryptoDepositOrder:
        if toman_amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        config = await self._get_active_config(provider_type)
        api_key = decrypt_secret(config.api_key_encrypted or "")

        order = CryptoDepositOrder(
            user_id=user_id,
            idempotency_key=uuid.uuid4().hex,
            provider_type=provider_type.value,
            currency=CryptoCurrency.TRX.value,
            toman_amount=toman_amount,
            status=CryptoDepositStatus.CREATED.value,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=_QUOTE_EXPIRY_SECONDS),
        )
        self.session.add(order)
        await self.session.flush()

        provider = build_payment_provider(provider_type.value, api_key=api_key, api_url=config.api_url or "")
        try:
            result = await provider.create_deposit_order(
                toman_amount=toman_amount,
                idempotency_key=order.idempotency_key,
            )
        finally:
            await provider.close()

        order.provider_order_id = result.provider_order_id
        order.crypto_amount = result.crypto_amount
        order.payment_url = result.payment_url
        order.expected_wallet_address = result.expected_wallet_address
        order.provider_reference = result.provider_reference
        order.status = CryptoDepositStatus.PENDING_PAYMENT.value

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def _get_locked_by_provider_order_id(self, provider_order_id: str) -> CryptoDepositOrder | None:
        result = await self.session.execute(
            select(CryptoDepositOrder)
            .where(CryptoDepositOrder.provider_order_id == provider_order_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def mark_verified_and_credit(self, order: CryptoDepositOrder) -> CryptoDepositOrder:
        """
        Credit نهایی کیف‌پول TRX کاربر. Idempotent: اگر order از قبل
        VERIFIED باشد، دوباره Credit نمی‌زند (چه این متد از Webhook صدا
        زده شود چه از یک Reconciliation دستی ادمین) - بند ۵ و ۱۸ سند.
        """
        if order.status == CryptoDepositStatus.VERIFIED.value:
            return order
        if order.crypto_amount is None:
            raise ValueError("مبلغ TRX سفارش هنوز مشخص نشده است.")

        await CryptoWalletService(self.session).credit(
            user_id=order.user_id,
            currency=CryptoCurrency(order.currency),
            amount=order.crypto_amount,
            type_=CryptoWalletTxType.DEPOSIT,
            reference_id=order.order_id,
            description=f"واریز TRX از طریق {order.provider_type}",
        )

        order.status = CryptoDepositStatus.VERIFIED.value
        order.verified_at = datetime.now(timezone.utc)
        await self.session.commit()
        return order

    async def handle_webhook(self, provider_type: PaymentProviderType, payload: dict, headers: dict) -> CryptoDepositOrder:
        """
        فلوی بند ۴ سند: Tronado Callback -> Verify -> TRX Wallet Credit.
        هرگز فقط بر مبنای محتوای payload اعتماد نمی‌شود - همیشه verify_deposit
        سمت Provider هم صدا زده می‌شود (بند ۲۲: Provider Verification).
        """
        config = await self._get_active_config(provider_type)
        api_key = decrypt_secret(config.api_key_encrypted or "")
        provider = build_payment_provider(provider_type.value, api_key=api_key, api_url=config.api_url or "")

        try:
            if not await provider.verify_webhook_signature(payload, headers):
                raise ValueError("امضای Webhook نامعتبر است.")

            parsed = await provider.handle_webhook(payload)
            provider_order_id = parsed.get("provider_order_id")
            if not provider_order_id:
                raise ValueError("Webhook فاقد provider_order_id است.")

            order = await self._get_locked_by_provider_order_id(provider_order_id)
            if order is None:
                raise DepositOrderNotFoundError(f"سفارش با provider_order_id={provider_order_id} پیدا نشد.")

            if order.status == CryptoDepositStatus.VERIFIED.value:
                return order  # Idempotent - Callback تکراری.

            verified = await provider.verify_deposit(provider_order_id)
            if not verified:
                order.status = CryptoDepositStatus.FAILED.value
                await self.session.commit()
                return order

            return await self.mark_verified_and_credit(order)
        finally:
            await provider.close()
