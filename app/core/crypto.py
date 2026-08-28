"""
رمزنگاری Credential پنل‌های VPN/Provider (بند ۳۴ و ۵۱ سند).

⚠️ تصمیم نهایی درباره‌ی مدیریت کلید (rotation، KMS، Vault و ...) در فاز
مستقل Security گرفته می‌شود (طبق تصمیم صریح کاربر). این پیاده‌سازی فعلی
یک راه‌حل *واقعی و امن برای شروع* است، نه Placeholder ساختگی:

- از Fernet (AES-128-CBC + HMAC، استاندارد کتابخانه‌ی cryptography) استفاده
  می‌شود؛ یعنی چیزی که در دیتابیس ذخیره می‌شود Cipher-text واقعی است، نه
  Base64 ساده یا متن خام.
- کلید از متغیر محیطی PANEL_ENCRYPTION_KEY خوانده می‌شود (هرگز Hard-code
  نشود). اگر تنظیم نشده باشد، فقط در ENVIRONMENT=development یک کلید
  موقت تولید و هشدار داده می‌شود تا توسعه متوقف نشود؛ در production بدون
  این متغیر برنامه بالا نمی‌آید.
- تغییر روش رمزنگاری در آینده (فاز Security) فقط همین فایل را تحت تاثیر
  قرار می‌دهد؛ بقیه‌ی کد فقط encrypt()/decrypt() را صدا می‌زند.
"""
from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings

logger = logging.getLogger("access_hub.crypto")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    settings = get_settings()
    key = settings.panel_encryption_key

    if not key:
        if settings.environment == "production":
            raise RuntimeError(
                "PANEL_ENCRYPTION_KEY تنظیم نشده است. برای رمزنگاری Credential "
                "پنل‌های VPN/Provider در Production این مقدار اجباری است. "
                "یک کلید با Fernet.generate_key() بساز و در .env قرار بده."
            )
        # فقط برای توسعه‌ی محلی: کلید موقت تا ری‌استارت بعدی معتبر است.
        key = Fernet.generate_key().decode()
        logger.warning(
            "PANEL_ENCRYPTION_KEY تنظیم نشده؛ یک کلید موقت توسعه تولید شد. "
            "این کلید با هر ری‌استارت عوض می‌شود و Credentialهای ذخیره‌شده "
            "غیرقابل بازیابی می‌شوند. قبل از Production حتماً مقدار ثابت تنظیم کن."
        )

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_secret(plain_text: str) -> str:
    """رشته‌ی خام (مثلاً پسورد پنل) را رمزنگاری و به شکل قابل‌ذخیره در DB برمی‌گرداند."""
    if not plain_text:
        return ""
    token = _get_fernet().encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(cipher_text: str) -> str:
    """مقدار رمزنگاری‌شده‌ی ذخیره در DB را به متن خام برمی‌گرداند."""
    if not cipher_text:
        return ""
    try:
        return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "امکان بازکردن رمز Credential وجود ندارد؛ احتمالاً PANEL_ENCRYPTION_KEY "
            "تغییر کرده است."
        ) from exc


def mask_secret(plain_text: str, visible: int = 3) -> str:
    """برای نمایش امن Credential در پنل ادمین (بند ۳۴: Masked/Encrypted)."""
    if not plain_text:
        return "—"
    if len(plain_text) <= visible:
        return "•" * len(plain_text)
    return plain_text[:visible] + "•" * max(len(plain_text) - visible, 4)
