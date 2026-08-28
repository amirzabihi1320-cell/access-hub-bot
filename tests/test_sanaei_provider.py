"""
تست‌های Provider واقعی Sanaei/3x-UI - با httpx.MockTransport، بدون نیاز
به یک پنل واقعی.
"""
import json
from datetime import datetime, timezone

import httpx
import pytest

from app.providers.exceptions import ProviderAuthError, ProviderNotFoundError
from app.providers.vpn.sanaei import SanaeiProvider, _deterministic_client_id
from app.providers.vpn.base import VPNUserCreateParams
from app.core.enums import HealthStatus


def _make_provider(handler, default_inbound_id=None) -> SanaeiProvider:
    provider = SanaeiProvider(
        base_url="https://panel.example.com",
        username="admin",
        password="secret",
        default_inbound_id=default_inbound_id,
    )
    provider._client = httpx.AsyncClient(
        base_url="https://panel.example.com",
        transport=httpx.MockTransport(handler),
    )
    return provider


def _traffic_obj(email: str, *, up=1000, down=2000, total=10 * 1024 ** 3, enable=True, expiry_ms=0) -> dict:
    return {
        "email": email,
        "up": up,
        "down": down,
        "total": total,
        "enable": enable,
        "expiryTime": expiry_ms,
    }


@pytest.mark.asyncio
async def test_authenticate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/login"
        return httpx.Response(200, json={"success": True})

    provider = _make_provider(handler)
    await provider.authenticate()
    assert provider._authenticated is True


@pytest.mark.asyncio
async def test_authenticate_bad_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False, "msg": "wrong username or password"})

    provider = _make_provider(handler)
    with pytest.raises(ProviderAuthError):
        await provider.authenticate()


@pytest.mark.asyncio
async def test_create_user_success_with_explicit_inbound():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/addClient":
            body = json.loads(request.content)
            assert body["id"] == 7
            settings = json.loads(body["settings"])
            client = settings["clients"][0]
            assert client["email"] == "ah_1_123"
            assert client["totalGB"] == 10 * 1024 ** 3
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/getClientTraffics/ah_1_123":
            return httpx.Response(200, json={"success": True, "obj": _traffic_obj("ah_1_123", up=0, down=0)})
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = _make_provider(handler, default_inbound_id=7)
    info = await provider.create_user(
        VPNUserCreateParams(username="ah_1_123", data_limit_bytes=10 * 1024 ** 3, expire_at=None)
    )
    assert info.username == "ah_1_123"
    assert info.status == "ACTIVE"
    assert info.used_traffic_bytes == 0


@pytest.mark.asyncio
async def test_create_user_auto_picks_first_enabled_inbound():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/list":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "obj": [
                        {"id": 1, "enable": False},
                        {"id": 2, "enable": True},
                    ],
                },
            )
        if request.url.path == "/panel/api/inbounds/addClient":
            body = json.loads(request.content)
            assert body["id"] == 2  # اولین Inbound فعال، نه اولین در لیست
            return httpx.Response(200, json={"success": True})
        if request.url.path.startswith("/panel/api/inbounds/getClientTraffics/"):
            return httpx.Response(200, json={"success": True, "obj": _traffic_obj("ah_2_1")})
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = _make_provider(handler, default_inbound_id=None)
    info = await provider.create_user(VPNUserCreateParams(username="ah_2_1"))
    assert info.username == "ah_2_1"


@pytest.mark.asyncio
async def test_get_user_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(200, json={"success": True, "obj": None})

    provider = _make_provider(handler, default_inbound_id=1)
    with pytest.raises(ProviderNotFoundError):
        await provider.get_user("does_not_exist")


@pytest.mark.asyncio
async def test_health_check_online():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/list":
            return httpx.Response(200, json={"success": True, "obj": [{"id": 1, "enable": True}]})
        raise AssertionError("unexpected path")

    provider = _make_provider(handler, default_inbound_id=1)
    health = await provider.health_check()
    assert health.status == HealthStatus.ONLINE


@pytest.mark.asyncio
async def test_health_check_offline_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = _make_provider(handler, default_inbound_id=1)
    health = await provider.health_check()
    assert health.status == HealthStatus.OFFLINE


@pytest.mark.asyncio
async def test_deterministic_client_id_is_stable():
    # این تست تضمین می‌کند که همیشه از یک username همان UUID تولید می‌شود -
    # یعنی modify/delete بعداً بدون ذخیره‌ی جداگانه‌ی UUID درست کار می‌کنند.
    id1 = _deterministic_client_id("ah_1_123")
    id2 = _deterministic_client_id("ah_1_123")
    id3 = _deterministic_client_id("ah_1_124")
    assert id1 == id2
    assert id1 != id3


@pytest.mark.asyncio
async def test_modify_user_preserves_unspecified_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path.startswith("/panel/api/inbounds/getClientTraffics/"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "obj": _traffic_obj("ah_1_123", total=5 * 1024 ** 3, expiry_ms=1893456000000),
                },
            )
        if "updateClient" in request.url.path:
            body = json.loads(request.content)
            settings = json.loads(body["settings"])
            client = settings["clients"][0]
            # data_limit_bytes مشخص نشده بود -> باید همان مقدار قبلی (current) حفظ شود
            assert client["totalGB"] == 5 * 1024 ** 3
            assert client["enable"] is False
            return httpx.Response(200, json={"success": True})
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = _make_provider(handler, default_inbound_id=1)
    await provider.modify_user("ah_1_123", status="DISABLED")


@pytest.mark.asyncio
async def test_reset_traffic_calls_correct_endpoint():
    called = {"reset": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login":
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/panel/api/inbounds/1/resetClientTraffic/ah_1_123":
            called["reset"] = True
            return httpx.Response(200, json={"success": True})
        if request.url.path.startswith("/panel/api/inbounds/getClientTraffics/"):
            return httpx.Response(200, json={"success": True, "obj": _traffic_obj("ah_1_123", up=0, down=0)})
        raise AssertionError(f"unexpected path {request.url.path}")

    provider = _make_provider(handler, default_inbound_id=1)
    info = await provider.reset_traffic("ah_1_123")
    assert called["reset"] is True
    assert info.used_traffic_bytes == 0
