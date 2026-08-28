"""
تست‌های Provider واقعی Marzban - بدون نیاز به یک پنل واقعی، با استفاده
از httpx.MockTransport (شبیه‌سازی پاسخ‌های سرور طبق مستندات Marzban).
"""
from datetime import datetime, timezone

import httpx
import pytest

from app.providers.exceptions import (
    ProviderAuthError,
    ProviderNotFoundError,
    ProviderValidationError,
)
from app.providers.vpn.marzban import MarzbanProvider
from app.providers.vpn.base import VPNUserCreateParams
from app.core.enums import HealthStatus


def _user_payload(username: str = "ah_1_123", status: str = "active") -> dict:
    return {
        "username": username,
        "status": status,
        "used_traffic": 1024,
        "data_limit": 10 * 1024 ** 3,
        "expire": int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp()),
        "subscription_url": f"https://panel.example.com/sub/{username}",
        "links": ["vless://uuid@panel.example.com:443?type=ws#test"],
    }


def _make_provider(handler) -> MarzbanProvider:
    provider = MarzbanProvider(base_url="https://panel.example.com", username="admin", password="secret")
    provider._client = httpx.AsyncClient(
        base_url="https://panel.example.com",
        transport=httpx.MockTransport(handler),
    )
    return provider


@pytest.mark.asyncio
async def test_authenticate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/admin/token"
        return httpx.Response(200, json={"access_token": "tok123", "token_type": "bearer"})

    provider = _make_provider(handler)
    await provider.authenticate()
    assert provider._token == "tok123"


@pytest.mark.asyncio
async def test_authenticate_bad_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Incorrect username or password"})

    provider = _make_provider(handler)
    with pytest.raises(ProviderAuthError):
        await provider.authenticate()


@pytest.mark.asyncio
async def test_create_user_success():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok123"})
        if request.url.path == "/api/user" and request.method == "POST":
            assert request.headers["Authorization"] == "Bearer tok123"
            return httpx.Response(200, json=_user_payload())
        raise AssertionError(f"unexpected request {request.method} {request.url.path}")

    provider = _make_provider(handler)
    info = await provider.create_user(
        VPNUserCreateParams(username="ah_1_123", data_limit_bytes=10 * 1024 ** 3, expire_at=None)
    )
    assert info.username == "ah_1_123"
    assert info.status == "ACTIVE"
    assert info.subscription_url.endswith("ah_1_123")
    assert info.config_links


@pytest.mark.asyncio
async def test_get_user_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok123"})
        return httpx.Response(404, json={"detail": "User not found"})

    provider = _make_provider(handler)
    with pytest.raises(ProviderNotFoundError):
        await provider.get_user("does_not_exist")


@pytest.mark.asyncio
async def test_create_user_duplicate_conflict():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok123"})
        return httpx.Response(409, json={"detail": "User already exists"})

    provider = _make_provider(handler)
    with pytest.raises(ProviderValidationError):
        await provider.create_user(VPNUserCreateParams(username="dup"))


@pytest.mark.asyncio
async def test_token_refresh_on_401():
    calls = {"token": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": f"tok{calls['token']}"})
        if request.url.path == "/api/user/ah_1_123":
            if request.headers["Authorization"] == "Bearer tok1":
                # اولین توکن منقضی شده فرض می‌شود.
                return httpx.Response(401, json={"detail": "expired"})
            return httpx.Response(200, json=_user_payload())
        raise AssertionError("unexpected path")

    provider = _make_provider(handler)
    info = await provider.get_user("ah_1_123")
    assert info.username == "ah_1_123"
    assert calls["token"] == 2  # یک‌بار اول، یک‌بار بعد از 401


@pytest.mark.asyncio
async def test_health_check_online():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok123"})
        if request.url.path == "/api/system":
            return httpx.Response(200, json={"version": "0.5.2", "users_active": 42, "total_user": 100})
        raise AssertionError("unexpected path")

    provider = _make_provider(handler)
    health = await provider.health_check()
    assert health.status == HealthStatus.ONLINE
    assert "42" in health.detail


@pytest.mark.asyncio
async def test_health_check_offline_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _make_provider(handler)
    health = await provider.health_check()
    assert health.status == HealthStatus.OFFLINE


@pytest.mark.asyncio
async def test_modify_user_partial_update_uses_ellipsis_sentinel():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok123"})
        if request.url.path == "/api/user/ah_1_123" and request.method == "PUT":
            import json as _json
            captured["body"] = _json.loads(request.content)
            return httpx.Response(200, json=_user_payload())
        raise AssertionError("unexpected path")

    provider = _make_provider(handler)
    await provider.modify_user("ah_1_123", status="DISABLED")
    # data_limit/expire نباید در بدنه باشند چون مقداردهی نشده‌اند (Ellipsis).
    assert "data_limit" not in captured["body"]
    assert "expire" not in captured["body"]
    assert captured["body"]["status"] == "disabled"
