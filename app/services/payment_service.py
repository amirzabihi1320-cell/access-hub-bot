from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.enums import WalletTransactionType
from app.models.payment_transaction import PaymentTransaction
from app.services.wallet_service import WalletService
from app.providers.payment.base import PaymentProviderError
from app.providers.payment.registry import build_payment_provider


class PaymentAlreadySettledError(Exception):
    pass


class PaymentService:
    """Coordinates external payment providers with the internal ledger."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_tronado_wallet_deposit(self, user_id: int, amount_toman: int) -> PaymentTransaction:
        if amount_toman <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")
        settings = get_settings()
        callback_url = settings.tronado_callback_url
        if not callback_url:
            base = settings.webhook_base_url
            if not base:
                raise ValueError("TRONADO_CALLBACK_URL یا WEBHOOK_BASE_URL تنظیم نشده است.")
            callback_url = base.rstrip("/") + "/payments/tronado/webhook"

        payment_id = f"AH-T-{uuid.uuid4().hex[:28]}"
        tx = PaymentTransaction(
            user_id=user_id,
            payment_id=payment_id,
            provider="TRONADO",
            purpose="WALLET_DEPOSIT",
            amount_toman=amount_toman,
            asset="TRX",
            status="PENDING",
        )
        self.session.add(tx)
        await self.session.flush()

        provider = build_payment_provider("TRONADO")
        try:
            quote = await provider.create_payment(
                payment_id=payment_id,
                amount_toman=amount_toman,
                callback_url=callback_url,
            )
        except Exception:
            tx.status = "FAILED"
            await self.session.commit()
            raise
        finally:
            await provider.close()

        tx.provider_reference = quote.provider_reference
        tx.asset_amount = str(quote.asset_amount)
        tx.payment_url = quote.payment_url
        tx.raw_payload = json.dumps(quote.raw or {}, ensure_ascii=False, default=str)
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    @staticmethod
    def _event_value(event: dict, *keys: str):
        for key in keys:
            if key in event and event[key] is not None:
                return event[key]
        return None

    async def handle_tronado_webhook(self, raw_body: bytes, signature: str) -> PaymentTransaction:
        provider = build_payment_provider("TRONADO")
        try:
            event = provider.verify_webhook(raw_body, signature)
            payment_id = self._event_value(event, "PaymentID", "paymentID", "payment_id", "PaymentId")
            if not payment_id:
                raise PaymentProviderError("Webhook بدون PaymentID دریافت شد.")

            result = await self.session.execute(
                select(PaymentTransaction)
                .where(PaymentTransaction.payment_id == str(payment_id))
                .with_for_update()
            )
            tx = result.scalar_one_or_none()
            if tx is None:
                raise PaymentProviderError("PaymentID ناشناخته است.")
            if tx.provider != "TRONADO":
                raise PaymentProviderError("Provider تراکنش با Tronado مطابقت ندارد.")
            if tx.status == "PAID":
                return tx

            status_id = self._event_value(event, "OrderStatusID", "orderStatusID", "status_id", "StatusID")
            is_paid = bool(self._event_value(event, "IsPaid", "isPaid", "is_paid")) or str(status_id) == "30"
            paid_toman = self._event_value(event, "UserPaidTomanAmount", "userPaidTomanAmount", "user_paid_toman_amount")
            provider_ref = self._event_value(event, "OrderID", "orderId", "TrndOrderID", "TrndOrderId", "id")
            txid = self._event_value(event, "TXID", "TxID", "txid", "TransactionID")

            if provider_ref and not tx.provider_reference:
                tx.provider_reference = str(provider_ref)
            if txid:
                tx.transaction_id = str(txid)
            tx.raw_payload = json.dumps(event, ensure_ascii=False, default=str)

            if not is_paid:
                tx.status = "REJECTED" if str(status_id) in {"40", "200"} else "PENDING"
                await self.session.commit()
                return tx

            if paid_toman is None:
                if not tx.provider_reference:
                    raise PaymentProviderError("پرداخت موفق بدون مبلغ پرداختی و شناسه Provider.")
                status = await provider.get_status(tx.provider_reference)
                paid_toman = status.user_paid_toman
                if status.transaction_id and not tx.transaction_id:
                    tx.transaction_id = status.transaction_id

            if paid_toman is None or int(paid_toman) <= 0:
                raise PaymentProviderError("مبلغ پرداخت موفق از Tronado قابل تشخیص نیست.")

            paid_amount = int(paid_toman)
            if paid_amount < tx.amount_toman:
                tx.status = "UNDERPAID"
                await self.session.commit()
                return tx

            # WalletService historically commits each ledger mutation. To make
            # webhook retries safe even across a process crash, first look for
            # the unique payment reference. If it already exists, the wallet was
            # credited by an earlier delivery of the same webhook.
            from app.models.wallet import WalletTransaction
            existing = await self.session.execute(
                select(WalletTransaction).where(
                    WalletTransaction.reference_id == f"payment:{tx.payment_id}"
                ).limit(1)
            )
            if existing.scalar_one_or_none() is None:
                await WalletService(self.session).credit(
                    user_id=tx.user_id,
                    amount=paid_amount,
                    type_=WalletTransactionType.DEPOSIT,
                    reference_id=f"payment:{tx.payment_id}",
                    description="شارژ خودکار کیف پول از طریق Tronado",
                )
            tx.paid_toman = paid_amount
            tx.status = "PAID"
            tx.verified_at = datetime.now(timezone.utc)
            await self.session.commit()
            return tx
        finally:
            await provider.close()
