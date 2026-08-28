"""
Provider رسمی Sanaei/3x-UI-compatible (بند ۱۳ سند).

بر اساس API رایج خانواده‌ی X-UI (نسخه‌ی 3x-ui/MHSanaei که امروز رایج‌ترین
Fork است؛ بیشتر Fork های دیگر مثل alireza0/x-ui همین شکل کلی را دارند):

    POST /login                                                  -> ورود (Session Cookie)
    GET  /panel/api/inbounds/list                                -> فهرست Inboundها
    POST /panel/api/inbounds/addClient                            -> افزودن کلاینت
    POST /panel/api/inbounds/{inbound_id}/updateClient/{uuid}     -> ویرایش کلاینت
    POST /panel/api/inbounds/{inbound_id}/delClient/{uuid}        -> حذف کلاینت
    GET  /panel/api/inbounds/getClientTraffics/{email}            -> ترافیک/وضعیت کلاینت
    POST /panel/api/inbounds/{inbound_id}/resetClientTraffic/{email} -> صفرکردن مصرف

⚠️ نکته‌ی صداقت فنی (بند ۵۹ - No Fake Automation)، حتی صریح‌تر از Marzban:
برخلاف Marzban که یک پروژه‌ی واحد است، «پنل‌های Sanaei» چندین Fork دارند
(3x-ui/MHSanaei، alireza0/x-ui، sanaei اصلی و ...) که در جزئیات جزئی
(مسیر دقیق، نام فیلد enable/limitIp، ساختار Response) ممکن است فرق کنند.
این پیاده‌سازی روی رایج‌ترین/فعال‌ترین Fork امروز (3x-ui) منطبق است.
قبل از اتصال به یک پنل واقعی، حتماً health_check() و یک create_user()
آزمایشی روی یک Sandbox تأیید شود. اگر فرمت پاسخ فرق داشت، فقط
_parse_traffic_response()/_build_client_payload() نیاز به اصلاح دارند.

نکته‌ی معماری مهم: برخلاف Marzban (که هر کاربر شیء مستقل با username
یکتا در کل پنل است)، در X-UI هر «کلاینت» متعلق به یک Inbound مشخص است و
با UUID شناسایی می‌شود، نه یک Username آزاد. برای این‌که رابط عمومی
BaseVPNProvider (که روی «username» طراحی شده) حفظ شود:
- ``email`` کلاینت روی X-UI = همان ``username`` ورودی ما (خوانا و قابل جستجو).
- UUID کلاینت به‌صورت Deterministic از روی همان username تولید می‌شود
  (uuid5) - یعنی نیازی به ذخیره‌ی جداگانه‌ی UUID در دیتابیس ما نیست؛ هر بار
  از روی username دوباره قابل محاسبه است.
"""
from __future__ import annotations

import json
import time
import uuid as uuid_lib
from datetime import datetime, timezone

import httpx

from app.core.enums import HealthStatus
from app.providers.base import ProviderHealth
from app.providers.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderNotFoundError,
    ProviderValidationError,
)
from app.providers.vpn.base import BaseVPNProvider, VPNUserCreateParams, VPNUserInfo

# Namespace ثابت فقط برای تولید Deterministic UUID از روی username - هیچ
# معنای امنیتی ندارد، صرفاً یک شناسه‌ی ثابت دلخواه است.
_UUID_NAMESPACE = uuid_lib.UUID("6f9c2b1a-7d3e-4a1c-9f5b-2e8d1c4a6b7f")

_STATUS_MAP_OUT = {
    True: "ACTIVE",
    False: "DISABLED",
}


def _deterministic_client_id(username: str) -> str:
    return str(uuid_lib.uuid5(_UUID_NAMESPACE, username))


class SanaeiProvider(BaseVPNProvider):
    provider_type = "SANAEI"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        default_inbound_id: int | None = None,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._default_inbound_id = default_inbound_id
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._authenticated = False
        self._cached_inbound_id: int | None = None

    # ---------- زیرساخت داخلی ----------

    async def authenticate(self) -> None:
        try:
            resp = await self._client.post(
                "/login",
                data={"username": self._username, "password": self._password},
            )
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"اتصال به پنل Sanaei/X-UI برقرار نشد: {exc}") from exc

        if resp.status_code >= 400:
            raise ProviderError(f"Sanaei login failed: HTTP {resp.status_code}", retryable=resp.status_code >= 500)

        try:
            data = resp.json()
        except ValueError:
            data = {}
        if data and data.get("success") is False:
            raise ProviderAuthError(data.get("msg") or "یوزرنیم/پسورد ادمین پنل اشتباه است.")

        # نشست (Session Cookie) روی self._client.cookies خودکار ذخیره می‌شود.
        self._authenticated = True

    async def _ensure_auth(self) -> None:
        if not self._authenticated:
            await self.authenticate()

    async def _request(self, method: str, path: str, *, retry_on_expired: bool = True, **kwargs) -> dict:
        await self._ensure_auth()
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"اتصال به پنل Sanaei/X-UI برقرار نشد: {exc}") from exc

        if resp.status_code in (401, 403) and retry_on_expired:
            self._authenticated = False
            await self._ensure_auth()
            return await self._request(method, path, retry_on_expired=False, **kwargs)

        if resp.status_code == 404:
            raise ProviderNotFoundError("مسیر/کلاینت روی پنل پیدا نشد.")
        if resp.status_code >= 500:
            raise ProviderError(f"خطای داخلی پنل (HTTP {resp.status_code})", retryable=True)
        if resp.status_code >= 400:
            raise ProviderError(f"پنل HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("پاسخ پنل قابل تفسیر نبود (JSON نامعتبر).", retryable=True) from exc

        if isinstance(data, dict) and data.get("success") is False:
            msg = data.get("msg") or "درخواست رد شد."
            if "not found" in msg.lower() or "پیدا نشد" in msg:
                raise ProviderNotFoundError(msg)
            raise ProviderValidationError(msg)

        return data

    async def _get_inbound_id(self) -> int:
        """
        اگر Panel.default_inbound_id تنظیم نشده باشد، اولین Inbound فعال
        پنل را (یک‌بار) کش می‌کند. کافی برای رایج‌ترین سناریو: یک پنل با
        یک Inbound اصلی. برای چند-Inbound، ادمین باید هنگام افزودن پنل
        default_inbound_id را صریح مشخص کند.
        """
        if self._default_inbound_id is not None:
            return self._default_inbound_id
        if self._cached_inbound_id is not None:
            return self._cached_inbound_id

        data = await self._request("GET", "/panel/api/inbounds/list")
        inbounds = data.get("obj") or []
        for inbound in inbounds:
            if inbound.get("enable", True):
                self._cached_inbound_id = inbound["id"]
                return self._cached_inbound_id
        raise ProviderValidationError("هیچ Inbound فعالی روی این پنل پیدا نشد.")

    def _build_client_payload(self, params: VPNUserCreateParams) -> dict:
        client_id = _deterministic_client_id(params.username)
        expire_ms = int(params.expire_at.timestamp() * 1000) if params.expire_at else 0
        return {
            "id": client_id,
            "flow": params.extra.get("flow", ""),
            "email": params.username,
            "limitIp": params.extra.get("limit_ip", 0),
            "totalGB": params.data_limit_bytes or 0,
            "expiryTime": expire_ms,
            "enable": True,
            "tgId": "",
            "subId": client_id[:16],
            "reset": 0,
            # برای Inboundهای Trojan/Shadowsocks که به‌جای uuid از password
            # استفاده می‌کنند - همان مقدار deterministic را می‌گذاریم تا
            # همچنان از روی username قابل بازتولید باشد.
            "password": client_id,
        }

    def _parse_traffic(self, obj: dict) -> VPNUserInfo:
        expire_ms = obj.get("expiryTime") or 0
        expire_at = datetime.fromtimestamp(expire_ms / 1000, tz=timezone.utc) if expire_ms else None
        used = int(obj.get("up") or 0) + int(obj.get("down") or 0)
        return VPNUserInfo(
            username=obj.get("email", ""),
            status=_STATUS_MAP_OUT.get(bool(obj.get("enable", True)), "ERROR"),
            data_limit_bytes=(obj.get("total") or None),
            used_traffic_bytes=used,
            expire_at=expire_at,
            subscription_url=None,  # X-UI معمولاً subscription را جدا از این Endpoint می‌سازد.
            config_links=[],
            raw=obj,
        )

    # ---------- BaseProvider ----------

    async def health_check(self) -> ProviderHealth:
        start = time.monotonic()
        try:
            data = await self._request("GET", "/panel/api/inbounds/list")
        except ProviderError as exc:
            return ProviderHealth(status=HealthStatus.OFFLINE, detail=exc.message)
        latency = (time.monotonic() - start) * 1000
        inbound_count = len(data.get("obj") or [])
        return ProviderHealth(
            status=HealthStatus.ONLINE,
            detail=f"{inbound_count} Inbound فعال/غیرفعال روی این پنل یافت شد.",
            latency_ms=round(latency, 1),
        )

    async def get_capacity_info(self) -> dict:
        data = await self._request("GET", "/panel/api/inbounds/list")
        inbounds = data.get("obj") or []
        total_clients = sum(len((ib.get("clientStats") or [])) for ib in inbounds)
        return {"current_users": total_clients}

    # ---------- BaseVPNProvider ----------

    async def create_user(self, params: VPNUserCreateParams) -> VPNUserInfo:
        inbound_id = await self._get_inbound_id()
        client = self._build_client_payload(params)
        await self._request(
            "POST",
            "/panel/api/inbounds/addClient",
            json={"id": inbound_id, "settings": json.dumps({"clients": [client]})},
        )
        # X-UI در پاسخ addClient معمولاً خودِ کلاینت را برنمی‌گرداند؛ برای
        # یک VPNUserInfo کامل (با used_traffic واقعی که تازه ساخته = 0)
        # بلافاصله traffic را می‌خوانیم.
        return await self.get_user(params.username)

    async def get_user(self, username: str) -> VPNUserInfo:
        data = await self._request("GET", f"/panel/api/inbounds/getClientTraffics/{username}")
        obj = data.get("obj")
        if not obj:
            raise ProviderNotFoundError(f"کلاینت «{username}» روی پنل پیدا نشد.")
        return self._parse_traffic(obj)

    async def modify_user(
        self,
        username: str,
        *,
        data_limit_bytes: int | None = ...,
        expire_at: datetime | None = ...,
        status: str | None = None,
    ) -> VPNUserInfo:
        inbound_id = await self._get_inbound_id()
        client_id = _deterministic_client_id(username)

        current = await self.get_user(username)
        params = VPNUserCreateParams(
            username=username,
            data_limit_bytes=(current.data_limit_bytes if data_limit_bytes is ... else data_limit_bytes),
            expire_at=(current.expire_at if expire_at is ... else expire_at),
        )
        client = self._build_client_payload(params)
        if status:
            client["enable"] = status.upper() == "ACTIVE"
        elif current.status:
            client["enable"] = current.status == "ACTIVE"

        await self._request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/updateClient/{client_id}",
            json={"id": inbound_id, "settings": json.dumps({"clients": [client]})},
        )
        return await self.get_user(username)

    async def delete_user(self, username: str) -> bool:
        inbound_id = await self._get_inbound_id()
        client_id = _deterministic_client_id(username)
        await self._request("POST", f"/panel/api/inbounds/{inbound_id}/delClient/{client_id}")
        return True

    async def revoke_user(self, username: str) -> VPNUserInfo:
        # X-UI مفهوم "Revoke UUID" مثل Marzban ندارد چون UUID اینجا
        # Deterministic از username است، نه Random. معادل نزدیک: حذف و
        # بازسازی کلاینت با همان تنظیمات (UUID یکسان باقی می‌ماند چون
        # deterministic است - برای Revoke واقعی، Username باید عوض شود
        # که در سطح VPNProvisioningService مدیریت می‌شود، نه اینجا).
        raise NotImplementedError("Revoke برای پنل‌های X-UI/Sanaei پشتیبانی نمی‌شود؛ به‌جایش delete+recreate کنید.")

    async def enable_user(self, username: str) -> VPNUserInfo:
        return await self.modify_user(username, status="ACTIVE")

    async def disable_user(self, username: str) -> VPNUserInfo:
        return await self.modify_user(username, status="DISABLED")

    async def reset_traffic(self, username: str) -> VPNUserInfo:
        inbound_id = await self._get_inbound_id()
        await self._request("POST", f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{username}")
        return await self.get_user(username)

    async def close(self) -> None:
        await self._client.aclose()
