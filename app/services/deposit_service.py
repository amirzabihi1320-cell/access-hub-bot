"""
مدیریت درخواست‌های شارژ دستی کیف پول (بخش ۹ سند).
تأیید/رد فقط یک‌بار روی هر درخواست ممکن است؛ برای جلوگیری از
Duplicate approval هنگام تصمیم‌گیری سطر DepositRequest قفل می‌شود.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DepositRequestStatus, WalletTransactionType
from app.models.deposit_request import DepositRequest
from app.services.wallet_service import WalletService


class DepositAlreadyDecidedError(Exception):
    """این درخواست قبلاً تأیید یا رد شده است."""


class DepositService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(self, user_id: int, amount: int) -> DepositRequest:
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")
        request = DepositRequest(
            user_id=user_id, amount=amount, status=DepositRequestStatus.PENDING.value
        )
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def attach_receipt(self, request_id: int, file_id: str) -> DepositRequest:
        request = await self.get(request_id)
        if request is None:
            raise ValueError("درخواست پیدا نشد.")
        request.receipt_file_id = file_id
        await self.session.commit()
        return request

    async def get(self, request_id: int) -> DepositRequest | None:
        result = await self.session.execute(
            select(DepositRequest).where(DepositRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def _get_locked(self, request_id: int) -> DepositRequest | None:
        result = await self.session.execute(
            select(DepositRequest).where(DepositRequest.id == request_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def approve(self, request_id: int, admin_id: int) -> DepositRequest:
        request = await self._get_locked(request_id)
        if request is None:
            raise ValueError("درخواست پیدا نشد.")
        if request.status != DepositRequestStatus.PENDING.value:
            raise DepositAlreadyDecidedError("این درخواست قبلاً بررسی شده است.")

        request.status = DepositRequestStatus.APPROVED.value
        request.decided_by_admin_id = admin_id
        request.decided_at = datetime.now(timezone.utc)
        await self.session.commit()

        # افزایش موجودی فقط از طریق WalletService و بعد از قطعی شدن تأیید
        await WalletService(self.session).credit(
            user_id=request.user_id,
            amount=request.amount,
            type_=WalletTransactionType.DEPOSIT,
            reference_id=f"deposit:{request.id}",
            description="تأیید شارژ دستی کیف پول",
            admin_id=admin_id,
        )
        return request

    async def reject(
        self, request_id: int, admin_id: int, reason: str | None = None
    ) -> DepositRequest:
        request = await self._get_locked(request_id)
        if request is None:
            raise ValueError("درخواست پیدا نشد.")
        if request.status != DepositRequestStatus.PENDING.value:
            raise DepositAlreadyDecidedError("این درخواست قبلاً بررسی شده است.")

        request.status = DepositRequestStatus.REJECTED.value
        request.decided_by_admin_id = admin_id
        request.decided_at = datetime.now(timezone.utc)
        request.reject_reason = reason
        await self.session.commit()
        return request
