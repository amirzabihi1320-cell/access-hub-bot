from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.core.enums import HealthStatus
from app.models.user import User
from app.models.vpn_panel import VPNPanel
from app.providers.base import ProviderHealth
from app.providers.exceptions import ProviderConnectionError
from app.providers.vpn.base import BaseVPNProvider, VPNUserCreateParams, VPNUserInfo
from app.services.user_service import UserService
from app.services.vpn_panel_service import VPNPanelService
from app.services.vpn_provisioning_service import NoAvailablePanelError, VPNProvisioningService


@pytest.fixture(autouse=True)
def _fake_settings(monkeypatch):
    """
    از وابستگی به یک .env واقعی صرف‌نظر می‌کند - این تست‌ها نباید به
    BOT_TOKEN/DATABASE_URL و ... نیاز داشته باشند، فقط به رمزنگاری.
    """
    class _FakeSettings:
        panel_encryption_key = "kY9V3sZ1n7q6Xh4wJb2mC8dR0pL5tF3aU9eN6yQ7wI4="  # فقط برای تست
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


async def _make_user(session: AsyncSession) -> User:
    return await UserService(session).get_or_create(111, "u", "U", None)


class _FakeProvider(BaseVPNProvider):
    provider_type = "FAKE"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.closed = False

    async def authenticate(self) -> None:
        return None

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(status=HealthStatus.ONLINE)

    async def create_user(self, params: VPNUserCreateParams) -> VPNUserInfo:
        if self.should_fail:
            raise ProviderConnectionError("panel down")
        return VPNUserInfo(
            username=params.username,
            status="ACTIVE",
            data_limit_bytes=params.data_limit_bytes,
            used_traffic_bytes=0,
            expire_at=params.expire_at,
            subscription_url=f"https://fake/{params.username}",
            config_links=["vless://fake"],
        )

    async def get_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    async def modify_user(self, username: str, **kwargs) -> VPNUserInfo:
        raise NotImplementedError

    async def delete_user(self, username: str) -> bool:
        return True

    async def revoke_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    async def enable_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    async def disable_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_provisions_on_highest_priority_panel(session: AsyncSession):
    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b", priority=10
    )

    provisioning = VPNProvisioningService(session)
    provisioning.panel_service.build_provider = lambda p: _FakeProvider(should_fail=False)

    service = await provisioning.provision_for_user(
        user_id=user.id,
        username_prefix="ah",
        data_limit_bytes=10 * 1024 ** 3,
        expire_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    assert service.panel_id == panel.id
    assert service.status == "ACTIVE"
    assert service.subscription_url.startswith("https://fake/")


@pytest.mark.asyncio
async def test_failover_to_second_panel_when_first_fails(session: AsyncSession):
    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel1 = await panel_service.create(
        name="P1-fails", panel_type="MARZBAN", base_url="https://p1", username="a", password="b", priority=10
    )
    panel2 = await panel_service.create(
        name="P2-works", panel_type="MARZBAN", base_url="https://p2", username="a", password="b", priority=20
    )

    provisioning = VPNProvisioningService(session)

    def fake_build_provider(panel: VPNPanel):
        return _FakeProvider(should_fail=(panel.id == panel1.id))

    provisioning.panel_service.build_provider = fake_build_provider

    service = await provisioning.provision_for_user(
        user_id=user.id,
        username_prefix="ah",
        data_limit_bytes=None,
        expire_at=None,
    )

    assert service.panel_id == panel2.id


@pytest.mark.asyncio
async def test_no_available_panel_raises_when_all_fail(session: AsyncSession):
    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b", priority=10
    )

    provisioning = VPNProvisioningService(session)
    provisioning.panel_service.build_provider = lambda p: _FakeProvider(should_fail=True)

    with pytest.raises(NoAvailablePanelError):
        await provisioning.provision_for_user(
            user_id=user.id, username_prefix="ah", data_limit_bytes=None, expire_at=None
        )


@pytest.mark.asyncio
async def test_no_available_panel_when_none_registered(session: AsyncSession):
    user = await _make_user(session)
    provisioning = VPNProvisioningService(session)

    with pytest.raises(NoAvailablePanelError):
        await provisioning.provision_for_user(
            user_id=user.id, username_prefix="ah", data_limit_bytes=None, expire_at=None
        )


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures(session: AsyncSession, monkeypatch):
    """بند ۲۸: خطای موقت (retryable) باید قبل از رفتن به پنل بعدی، چند بار روی همان پنل Retry شود."""
    import app.services.vpn_provisioning_service as mod

    sleeps = []
    monkeypatch.setattr(mod.asyncio, "sleep", lambda s: sleeps.append(s))

    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )

    attempts = {"n": 0}

    class _FlakyProvider(_FakeProvider):
        async def create_user(self, params):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise ProviderConnectionError("temporary")
            return await super().create_user(params)

    provisioning = VPNProvisioningService(session)
    provisioning.panel_service.build_provider = lambda p: _FlakyProvider(should_fail=False)

    service = await provisioning.provision_for_user(
        user_id=user.id, username_prefix="ah", data_limit_bytes=None, expire_at=None
    )

    assert service.panel_id == panel.id
    assert attempts["n"] == 3
    assert len(sleeps) == 2  # دو بار Retry قبل از موفقیت در تلاش سوم


@pytest.mark.asyncio
async def test_non_retryable_error_skips_retry_and_goes_to_next_panel(session: AsyncSession, monkeypatch):
    """خطای غیرقابل‌تلاش‌مجدد (مثل Validation/Duplicate) نباید Retry شود - مستقیم پنل بعدی."""
    import app.services.vpn_provisioning_service as mod
    from app.providers.exceptions import ProviderValidationError

    sleep_calls = {"n": 0}
    monkeypatch.setattr(mod.asyncio, "sleep", lambda s: sleep_calls.__setitem__("n", sleep_calls["n"] + 1))

    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel1 = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b", priority=10
    )
    panel2 = await panel_service.create(
        name="P2", panel_type="MARZBAN", base_url="https://p2", username="a", password="b", priority=20
    )

    class _NonRetryableProvider(_FakeProvider):
        async def create_user(self, params):
            raise ProviderValidationError("duplicate username")

    def fake_build_provider(panel):
        if panel.id == panel1.id:
            return _NonRetryableProvider(should_fail=True)
        return _FakeProvider(should_fail=False)

    provisioning = VPNProvisioningService(session)
    provisioning.panel_service.build_provider = fake_build_provider

    service = await provisioning.provision_for_user(
        user_id=user.id, username_prefix="ah", data_limit_bytes=None, expire_at=None
    )

    assert service.panel_id == panel2.id
    assert sleep_calls["n"] == 0  # هیچ Retry ای برای خطای غیرموقت انجام نشده


@pytest.mark.asyncio
async def test_panel_credentials_round_trip_encryption(session: AsyncSession):
    panel_service = VPNPanelService(session)
    panel = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="admin", password="s3cret!",
    )
    # در DB باید Cipher-text باشد، نه پسورد خام.
    assert panel.password_encrypted != "s3cret!"
    from app.core.crypto import decrypt_secret

    assert decrypt_secret(panel.password_encrypted) == "s3cret!"


class _RetryOnceThenSucceedProvider(_FakeProvider):
    """اولین تلاش با خطای موقت Fail می‌شود، تلاش دوم موفق است."""

    def __init__(self):
        super().__init__(should_fail=False)
        self.attempts = 0

    async def create_user(self, params):
        self.attempts += 1
        if self.attempts == 1:
            from app.providers.exceptions import ProviderConnectionError

            raise ProviderConnectionError("temporary glitch")
        return await super().create_user(params)


@pytest.mark.asyncio
async def test_retryable_error_succeeds_on_second_attempt_same_panel(session: AsyncSession, monkeypatch):
    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )
    fake = _RetryOnceThenSucceedProvider()

    provisioning = VPNProvisioningService(session)
    provisioning.RETRY_DELAYS_SECONDS = (0.01, 0.01, 0.01)  # تست کند نشود
    provisioning.panel_service.build_provider = lambda p: fake

    service = await provisioning.provision_for_user(
        user_id=user.id, username_prefix="ah", data_limit_bytes=None, expire_at=None
    )

    assert service.panel_id == panel.id
    assert fake.attempts == 2


@pytest.mark.asyncio
async def test_renew_service_extends_expiry_and_resets_traffic(session: AsyncSession):
    user = await _make_user(session)
    panel_service = VPNPanelService(session)
    panel = await panel_service.create(
        name="P1", panel_type="MARZBAN", base_url="https://p1", username="a", password="b"
    )

    provisioning = VPNProvisioningService(session)
    provisioning.panel_service.build_provider = lambda p: _FakeProvider(should_fail=False)

    original = await provisioning.provision_for_user(
        user_id=user.id,
        username_prefix="ah",
        data_limit_bytes=10 * 1024 ** 3,
        expire_at=datetime.now(timezone.utc) + timedelta(days=5),
    )
    old_expire = original.expire_at

    class _RenewProvider(_FakeProvider):
        async def modify_user(self, username, **kwargs):
            return VPNUserInfo(
                username=username,
                status="ACTIVE",
                data_limit_bytes=kwargs.get("data_limit_bytes"),
                used_traffic_bytes=999,  # قبل از reset
                expire_at=kwargs.get("expire_at"),
                subscription_url=f"https://fake/{username}",
                config_links=["vless://renewed"],
            )

        async def reset_traffic(self, username):
            return VPNUserInfo(
                username=username,
                status="ACTIVE",
                data_limit_bytes=20 * 1024 ** 3,
                used_traffic_bytes=0,  # بعد از reset
                expire_at=old_expire + timedelta(days=30),
                subscription_url=f"https://fake/{username}",
                config_links=["vless://renewed"],
            )

    provisioning.panel_service.build_provider = lambda p: _RenewProvider()

    renewed = await provisioning.renew_service(original.id, extra_days=30, new_data_limit_bytes=20 * 1024 ** 3)

    assert renewed.expire_at > old_expire
    assert renewed.used_traffic_bytes == 0  # ترافیک صفر شد
    assert renewed.data_limit_bytes == 20 * 1024 ** 3
