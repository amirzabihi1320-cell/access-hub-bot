"""
مدیریت درخواست‌های شارژ دستی کیف پول و Access Token.

RIAL:
    شارژ موجودی ریالی کیف پول

TOKEN:
    شارژ Access Token بازی

هر درخواست فقط یک‌بار قابل تأیید یا رد شدن است.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DepositRequestStatus, WalletTransactionType
from app.models.deposit_request import DepositRequest
from app.services.game_service import TokenService
from app.services.wallet_service import WalletService


class DepositAlreadyDecidedError(Exception):
    """این درخواست قبلاً تأیید یا رد شده است."""


class DepositService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_request(
        self,
        user_id: int,
        amount: int,
        deposit_type: str = "RIAL",
        token_amount: int | None = None,
    ) -> DepositRequest:

        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        if deposit_type not in {"RIAL", "TOKEN"}:
            raise ValueError("نوع شارژ نامعتبر است.")

        if deposit_type == "TOKEN":
            if token_amount is None or token_amount <= 0:
                raise ValueError("مقدار Token نامعتبر است.")

        if deposit_type == "RIAL":
            token_amount = None

        request = DepositRequest(
            user_id=user_id,
            amount=amount,
            deposit_type=deposit_type,
            token_amount=token_amount,
            status=DepositRequestStatus.PENDING.value,
        )

        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)

        return request

    async def attach_receipt(
        self,
        request_id: int,
        file_id: str,
    ) -> DepositRequest:

        request = await self.get(request_id)

        if request is None:
            raise ValueError("درخواست پیدا نشد.")

        if request.status != DepositRequestStatus.PENDING.value:
            raise DepositAlreadyDecidedError(
                "این درخواست قبلاً بررسی شده است."
            )

        request.receipt_file_id = file_id

        await self.session.commit()

        return request

    async def get(
        self,
        request_id: int,
    ) -> DepositRequest | None:

        result = await self.session.execute(
            select(DepositRequest).where(
                DepositRequest.id == request_id
            )
        )

        return result.scalar_one_or_none()

    async def _get_locked(
        self,
        request_id: int,
    ) -> DepositRequest | None:

        result = await self.session.execute(
            select(DepositRequest)
            .where(DepositRequest.id == request_id)
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def approve(
        self,
        request_id: int,
        admin_id: int,
    ) -> DepositRequest:

        request = await self._get_locked(request_id)

        if request is None:
            raise ValueError("درخواست پیدا نشد.")

        if request.status != DepositRequestStatus.PENDING.value:
            raise DepositAlreadyDecidedError(
                "این درخواست قبلاً بررسی شده است."
            )

        request.status = DepositRequestStatus.APPROVED.value
        request.decided_by_admin_id = admin_id
        request.decided_at = datetime.now(timezone.utc)

        if request.deposit_type == "RIAL":

            await WalletService(self.session).credit(
                user_id=request.user_id,
                amount=request.amount,
                type_=WalletTransactionType.DEPOSIT,
                reference_id=f"deposit:{request.id}",
                description="تأیید شارژ دستی کیف پول",
                admin_id=admin_id,
            )

        elif request.deposit_type == "TOKEN":

            if not request.token_amount:
                raise ValueError(
                    "مقدار Token برای این درخواست ثبت نشده است."
                )

            await TokenService(self.session).credit(
                user_id=request.user_id,
                amount=request.token_amount,
                type_="purchase",
                reference_id=f"token_deposit:{request.id}",
                description="تأیید شارژ دستی Access Token",
            )

            # TokenService.credit فقط رکوردها را تغییر می‌دهد و commit نمی‌کند.
            # بنابراین وضعیت درخواست و افزایش Token را همین‌جا یکجا ذخیره می‌کنیم.
            await self.session.commit()

        else:
            raise ValueError("نوع شارژ نامعتبر است.")

        return request

    async def reject(
        self,
        request_id: int,
        admin_id: int,
        reason: str | None = None,
    ) -> DepositRequest:

        request = await self._get_locked(request_id)

        if request is None:
            raise ValueError("درخواست پیدا نشد.")

        if request.status != DepositRequestStatus.PENDING.value:
            raise DepositAlreadyDecidedError(
                "این درخواست قبلاً بررسی شده است."
            )

        request.status = DepositRequestStatus.REJECTED.value
        request.decided_by_admin_id = admin_id
        request.decided_at = datetime.now(timezone.utc)
        request.reject_reason = reason

        await self.session.commit()

        return request

    async def list_pending(
        self,
        limit: int = 20,
    ) -> list[DepositRequest]:

        result = await self.session.execute(
            select(DepositRequest)
            .where(
                DepositRequest.status
                == DepositRequestStatus.PENDING.value
            )
            .order_by(DepositRequest.created_at)
            .limit(limit)
        )

        return list(result.scalars().all())

    async def count_pending(self) -> int:

        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(DepositRequest)
            .where(
                DepositRequest.status
                == DepositRequestStatus.PENDING.value
            )
        )

        return result.scalar_one()
