from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.enums import OrderStatus
from app.database.base import Base
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.auto_delivery_service import try_auto_deliver_vpn
from app.services.user_service import UserService
from app.services.vpn_panel_service import VPNPanelService
from app.services.vpn_provisioning_service import VPNProvisioningService
from app.providers.vpn.base import BaseVPNProvider, VPNUserInfo
from app.providers.base import ProviderHealth
from app.providers.exceptions import ProviderConnectionError
from app.core.enums import HealthStatus


@pytest.fixture(autouse=True)
def _fake_settings(monkeypatch):
    class _FakeSettings:
        panel_encryption_key = "kY9V3sZ1n7q6Xh4wJb2mC8dR0pL5tF3aU9eN6yQ7wI4="
        environment = "development"

    import app.core.crypto as crypto_module

    monkeypatch.setattr(crypto_module, "get_settings", lambda: _FakeSettings())
    crypto_module._fernet = None
    yield
    crypto_module._fernet = None


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


class _FakeProvider(BaseVPNProvider):
    provider_type = "FAKE"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def authenticate(self) -> None:
        return None

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status=HealthStatus.ONLINE)

    async def create_user(self, params):
        if self.should_fail:
            raise ProviderConnectionError("down")
        return VPNUserInfo(
            username=params.username,
            status="ACTIVE",
            data_limit_bytes=params.data_limit_bytes,
            used_traffic_bytes=0,
            expire_at=params.expire_at,
            subscription_url=f"https://fake/{params.username}",
            config_links=["vless://fake"],
        )

    async def get_user(self, username):
        raise NotImplementedError

    async def modify_user(self, username, **kwargs):
        raise NotImplementedError

    async def delete_user(self, username):
        return True

    async def revoke_user(self, username):
        raise NotImplementedError

    async def enable_user(self, username):
        raise NotImplementedError

    async def disable_user(self, username):
        raise NotImplementedError

    async def close(self) -> None:
        return None


async def _make_user(session: AsyncSession) -> User:
    return await UserService(session).get_or_create(111, "u", "U", None)


async def _make_vpn_product(session: AsyncSession, *, limit_gb: int | None = 30, duration_days: int | None = 30) -> Product:
    category = Category(name="VPN", icon="🔐", status=True, sort_order=0)
    session.add(category)
    await session.flush()
    product = Product(
        category_id=category.id,
        name="VPN 30GB/30d",
        slug="vpn-30-30",
        product_type="FIXED",
        fixed_price=100_000,
        is_vpn_product=True,
        vpn_data_limit_gb=limit_gb,
        vpn_duration_days=duration_days,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def _make_order(session: AsyncSession, user: User, product: Product) -> Order:
    order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=1,
        unit_price=product.fixed_price,
        final_price=product.fixed_price,
        status=OrderStatus.WAITING_ADMIN.value,
        delivery_type="MANUAL",
    )
    session.add(order)
    await session.flush()
    order.order_number = f"AH-{order.id:06d}"
    await session.commit()
    await session.refresh(order)
    return order


@pytest.mark.asyncio
async def test_non_vpn_product_is_noop(session: AsyncSession):
    user = await _make_user(session)
    product = await _make_vpn_product(session)
    product.is_vpn_product = False
    await session.commit()
    order = await _make_order(session, user, product)

    delivered, text = await try_auto_deliver_vpn(session, order, product)
    assert delivered is False
    assert text == ""
    assert order.status == OrderStatus.WAITING_ADMIN.value


@pytest.mark.asyncio
async def test_successful_auto_delivery_completes_order(session: AsyncSession, monkeypatch):
    user = await _make_user(session)
    product = await _make_vpn_product(session)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FakeProvider(should_fail=False))

    delivered, text = await try_auto_deliver_vpn(session, order, product)

    assert delivered is True
    assert "سرویس VPN شما آماده شد" in text
    assert order.status == OrderStatus.COMPLETED.value
    assert order.delivery_data and "subscription_url" in order.delivery_data


@pytest.mark.asyncio
async def test_all_panels_failing_leaves_order_for_manual_review(session: AsyncSession, monkeypatch):
    user = await _make_user(session)
    product = await _make_vpn_product(session)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FakeProvider(should_fail=True))

    delivered, text = await try_auto_deliver_vpn(session, order, product)

    assert delivered is False
    assert text == ""
    # وضعیت دست‌نخورده می‌ماند تا مسیر تحویل دستی موجود (mark_delivered) کار کند.
    assert order.status == OrderStatus.WAITING_ADMIN.value


@pytest.mark.asyncio
async def test_unlimited_traffic_and_no_expiry_product(session: AsyncSession, monkeypatch):
    user = await _make_user(session)
    product = await _make_vpn_product(session, limit_gb=None, duration_days=None)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)

    captured = {}

    class _CapturingProvider(_FakeProvider):
        async def create_user(self, params):
            captured["data_limit_bytes"] = params.data_limit_bytes
            captured["expire_at"] = params.expire_at
            return await super().create_user(params)

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _CapturingProvider())

    delivered, _ = await try_auto_deliver_vpn(session, order, product)

    assert delivered is True
    assert captured["data_limit_bytes"] is None
    assert captured["expire_at"] is None


# ---------- Auto-Renew (بند ۱۹) ----------


@pytest.mark.asyncio
async def test_auto_renew_success_debits_wallet_and_extends_service(session: AsyncSession, monkeypatch):
    from app.services.auto_delivery_service import try_auto_renew_vpn
    from app.services.wallet_service import WalletService
    from app.core.enums import WalletTransactionType
    from app.providers.vpn.base import VPNUserInfo

    user = await _make_user(session)
    product = await _make_vpn_product(session, limit_gb=20, duration_days=30)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FakeProvider(should_fail=False))
    delivered, _ = await try_auto_deliver_vpn(session, order, product)
    assert delivered is True

    from app.models.vpn_service import VPNService
    from sqlalchemy import select

    service = (await session.execute(select(VPNService).where(VPNService.order_id == order.id))).scalar_one()

    # کیف‌پول را شارژ کن تا بتواند هزینه‌ی تمدید را بدهد.
    await WalletService(session).credit(
        user_id=user.id, amount=product.fixed_price, type_=WalletTransactionType.DEPOSIT, reference_id="topup"
    )
    balance_before = await WalletService(session).get_balance(user.id)

    class _RenewProvider(_FakeProvider):
        async def modify_user(self, username, **kwargs):
            return VPNUserInfo(
                username=username, status="ACTIVE", data_limit_bytes=kwargs.get("data_limit_bytes"),
                used_traffic_bytes=0, expire_at=kwargs.get("expire_at"),
                subscription_url=f"https://fake/{username}", config_links=["vless://renewed"],
            )

        async def reset_traffic(self, username):
            return await self.modify_user(username, data_limit_bytes=20 * 1024 ** 3, expire_at=None)

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _RenewProvider())

    ok, text = await try_auto_renew_vpn(session, user.id, service.id)

    assert ok is True
    assert "تمدید شد" in text
    balance_after = await WalletService(session).get_balance(user.id)
    assert balance_after == balance_before - product.fixed_price


@pytest.mark.asyncio
async def test_auto_renew_insufficient_balance(session: AsyncSession, monkeypatch):
    from app.services.auto_delivery_service import try_auto_renew_vpn

    user = await _make_user(session)
    product = await _make_vpn_product(session)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)
    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FakeProvider(should_fail=False))
    await try_auto_deliver_vpn(session, order, product)

    from app.models.vpn_service import VPNService
    from sqlalchemy import select

    service = (await session.execute(select(VPNService).where(VPNService.order_id == order.id))).scalar_one()

    # کیف‌پول کاربر تازه صفر است (هیچ شارژی انجام نشده).
    ok, text = await try_auto_renew_vpn(session, user.id, service.id)

    assert ok is False
    assert "موجودی" in text


@pytest.mark.asyncio
async def test_auto_renew_provider_failure_refunds_wallet(session: AsyncSession, monkeypatch):
    from app.services.auto_delivery_service import try_auto_renew_vpn
    from app.services.wallet_service import WalletService
    from app.core.enums import WalletTransactionType

    user = await _make_user(session)
    product = await _make_vpn_product(session)
    await VPNPanelService(session).create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    order = await _make_order(session, user, product)
    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FakeProvider(should_fail=False))
    await try_auto_deliver_vpn(session, order, product)

    from app.models.vpn_service import VPNService
    from sqlalchemy import select

    service = (await session.execute(select(VPNService).where(VPNService.order_id == order.id))).scalar_one()

    await WalletService(session).credit(
        user_id=user.id, amount=product.fixed_price, type_=WalletTransactionType.DEPOSIT, reference_id="topup"
    )
    balance_before = await WalletService(session).get_balance(user.id)

    class _FailingRenewProvider(_FakeProvider):
        async def modify_user(self, username, **kwargs):
            raise ProviderConnectionError("panel down during renew")

    async def _no_sleep(*_a, **_k):
        return None

    monkeypatch.setattr(VPNPanelService, "build_provider", lambda self, panel: _FailingRenewProvider())
    monkeypatch.setattr("app.core.retry.asyncio.sleep", _no_sleep)

    ok, text = await try_auto_renew_vpn(session, user.id, service.id)

    assert ok is False
    balance_after = await WalletService(session).get_balance(user.id)
    # چون Provider Fail شد، پول باید کامل برگردد (بدون کسری خالص).
    assert balance_after == balance_before
