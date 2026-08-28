"""
Provider رسمی Marzban (بند ۱۲ سند).

بر اساس API رسمی Marzban (FastAPI-based, مستندات /docs روی خود پنل):
    POST   /api/admin/token          -> ورود ادمین (OAuth2 password flow)
    GET    /api/system                -> وضعیت/ظرفیت سرور
    POST   /api/user                  -> ساخت کاربر
    GET    /api/user/{username}       -> دریافت کاربر
    PUT    /api/user/{username}       -> ویرایش کاربر
    DELETE /api/user/{username}       -> حذف کاربر
    POST   /api/user/{username}/revoke_sub -> ابطال و تولید مجدد UUID/لینک‌ها
    GET    /api/users                 -> فهرست کاربران (برای ظرفیت)

⚠️ نکته‌ی صداقت فنی (بند ۵۹ سند - No Fake Automation): نام دقیق فیلدها
بین نسخه‌های مختلف Marzban کمی تفاوت دارد (مثلاً data_limit_reset_strategy
یا ساختار proxies/inbounds). این پیاده‌سازی روی رایج‌ترین نسخه‌های فعلی
منطبق است؛ قبل از اتصال به یک پنل واقعی، حتماً با health_check() و یک
create_user() تستی روی یک Sandbox تأیید شود. اگر پاسخ پنل با فرض‌های این
فایل فرق داشت، فقط _parse_user() نیاز به اصلاح دارد - بقیه‌ی سیستم دست‌نخورده می‌ماند.
"""
from __future__ import annotations

import time
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

_STATUS_MAP_OUT = {
    "active": "ACTIVE",
    "disabled": "DISABLED",
    "limited": "EXPIRED",
    "expired": "EXPIRED",
    "on_hold": "DISABLED",
}


class MarzbanProvider(BaseVPNProvider):
    provider_type = "MARZBAN"

    def __init__(self, base_url: str, username: str, password: str, *, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._token: str | None = None
        self._token_fetched_at: float = 0.0

    # ---------- زیرساخت داخلی ----------

    async def authenticate(self) -> None:
        try:
            resp = await self._client.post(
                "/api/admin/token",
                data={"username": self._username, "password": self._password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"اتصال به Marzban برقرار نشد: {exc}") from exc

        if resp.status_code in (401, 403):
            raise ProviderAuthError("یوزرنیم/پسورد ادمین Marzban اشتباه است.")
        if resp.status_code >= 400:
            raise ProviderError(f"Marzban login failed: HTTP {resp.status_code}", retryable=resp.status_code >= 500)

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise ProviderAuthError("پاسخ لاگین Marzban فاقد access_token بود.")
        self._token = token
        self._token_fetched_at = time.monotonic()

    async def _ensure_auth(self) -> None:
        if not self._token:
            await self.authenticate()

    async def _request(self, method: str, path: str, *, retry_on_401: bool = True, **kwargs) -> httpx.Response:
        await self._ensure_auth()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        try:
            resp = await self._client.request(method, path, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"اتصال به Marzban برقرار نشد: {exc}") from exc

        if resp.status_code in (401, 403) and retry_on_401:
            # توکن احتمالاً منقضی شده؛ یک‌بار دوباره لاگین و تلاش کن.
            self._token = None
            await self._ensure_auth()
            return await self._request(method, path, retry_on_401=False, **kwargs)

        if resp.status_code == 404:
            raise ProviderNotFoundError("کاربر/موجودیت در Marzban پیدا نشد.")
        if resp.status_code == 409:
            raise ProviderValidationError("این نام کاربری قبلاً روی Marzban وجود دارد.")
        if resp.status_code in (400, 422):
            raise ProviderValidationError(f"Marzban درخواست را رد کرد: {resp.text[:200]}")
        if resp.status_code >= 500:
            raise ProviderError(f"خطای داخلی Marzban (HTTP {resp.status_code})", retryable=True)
        if resp.status_code >= 400:
            raise ProviderError(f"Marzban HTTP {resp.status_code}: {resp.text[:200]}")

        return resp

    def _parse_user(self, data: dict) -> VPNUserInfo:
        expire_ts = data.get("expire")
        expire_at = (
            datetime.fromtimestamp(expire_ts, tz=timezone.utc) if expire_ts else None
        )
        raw_status = (data.get("status") or "active").lower()
        return VPNUserInfo(
            username=data["username"],
            status=_STATUS_MAP_OUT.get(raw_status, "ERROR"),
            data_limit_bytes=data.get("data_limit") or None,
            used_traffic_bytes=int(data.get("used_traffic") or 0),
            expire_at=expire_at,
            subscription_url=data.get("subscription_url"),
            config_links=list(data.get("links") or []),
            raw=data,
        )

    # ---------- BaseProvider ----------

    async def health_check(self) -> ProviderHealth:
        start = time.monotonic()
        try:
            resp = await self._request("GET", "/api/system")
        except ProviderError as exc:
            return ProviderHealth(status=HealthStatus.OFFLINE, detail=exc.message)
        latency = (time.monotonic() - start) * 1000
        data = resp.json()
        status = HealthStatus.ONLINE
        detail = f"نسخه {data.get('version', '?')} | کاربران فعال: {data.get('users_active', '?')}"
        return ProviderHealth(status=status, detail=detail, latency_ms=round(latency, 1))

    async def get_balance(self) -> float | None:
        # Marzban مفهوم "موجودی حساب" ندارد (Self-hosted است، نه یک سرویس Reseller).
        return None

    async def get_capacity_info(self) -> dict:
        resp = await self._request("GET", "/api/system")
        data = resp.json()
        return {
            "current_users": data.get("total_user"),
            "active_users": data.get("users_active"),
        }

    # ---------- BaseVPNProvider ----------

    async def create_user(self, params: VPNUserCreateParams) -> VPNUserInfo:
        payload = {
            "username": params.username,
            "proxies": params.extra.get("proxies") or {"vless": {}, "vmess": {}},
            "inbounds": params.extra.get("inbounds") or (
                {"vless": params.inbound_tags} if params.inbound_tags else {}
            ),
            "data_limit": params.data_limit_bytes or 0,
            "data_limit_reset_strategy": "no_reset",
            "expire": int(params.expire_at.timestamp()) if params.expire_at else None,
            "status": "active",
            "note": params.note or "",
        }
        resp = await self._request("POST", "/api/user", json=payload)
        return self._parse_user(resp.json())

    async def get_user(self, username: str) -> VPNUserInfo:
        resp = await self._request("GET", f"/api/user/{username}")
        return self._parse_user(resp.json())

    async def modify_user(
        self,
        username: str,
        *,
        data_limit_bytes: int | None = ...,
        expire_at: datetime | None = ...,
        status: str | None = None,
    ) -> VPNUserInfo:
        payload: dict = {}
        if data_limit_bytes is not ...:
            payload["data_limit"] = data_limit_bytes or 0
        if expire_at is not ...:
            payload["expire"] = int(expire_at.timestamp()) if expire_at else None
        if status:
            reverse_map = {"ACTIVE": "active", "DISABLED": "disabled"}
            payload["status"] = reverse_map.get(status, status.lower())
        resp = await self._request("PUT", f"/api/user/{username}", json=payload)
        return self._parse_user(resp.json())

    async def delete_user(self, username: str) -> bool:
        await self._request("DELETE", f"/api/user/{username}")
        return True

    async def revoke_user(self, username: str) -> VPNUserInfo:
        resp = await self._request("POST", f"/api/user/{username}/revoke_sub")
        return self._parse_user(resp.json())

    async def reset_traffic(self, username: str) -> VPNUserInfo:
        resp = await self._request("POST", f"/api/user/{username}/reset")
        return self._parse_user(resp.json())

    async def enable_user(self, username: str) -> VPNUserInfo:
        return await self.modify_user(username, status="ACTIVE")

    async def disable_user(self, username: str) -> VPNUserInfo:
        return await self.modify_user(username, status="DISABLED")

    async def reset_traffic(self, username: str) -> None:
        await self._request("POST", f"/api/user/{username}/reset")

    async def close(self) -> None:
        await self._client.aclose()
