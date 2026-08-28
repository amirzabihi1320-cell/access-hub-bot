"""
سلسله‌مراتب خطای Provider Engine (بند ۹ و ۵۸ سند).

قانون مهم: خطای فنی واقعی (مثلاً "Marzban API returned 500") هرگز مستقیم
به کاربر نمایش داده نمی‌شود. سرویس‌های بالادستی (VPNProvisioningService و
...) این Exceptionها را می‌گیرند، پیام کاربرپسند نشان می‌دهند و متن دقیق
خطا را فقط در Log/Audit ثبت می‌کنند.
"""
from __future__ import annotations


class ProviderError(Exception):
    """خطای پایه‌ی همه‌ی خطاهای Provider Engine."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ProviderAuthError(ProviderError):
    """احراز هویت با Provider ناموفق بود (Credential اشتباه/منقضی)."""

    def __init__(self, message: str = "احراز هویت با Provider ناموفق بود."):
        super().__init__(message, retryable=False)


class ProviderConnectionError(ProviderError):
    """Provider در دسترس نیست (Timeout، DNS، اتصال قطع و ...) - قابل Retry."""

    def __init__(self, message: str = "اتصال به Provider برقرار نشد."):
        super().__init__(message, retryable=True)


class ProviderNotFoundError(ProviderError):
    """موجودیت درخواستی (کاربر/سفارش/سرویس) در سمت Provider پیدا نشد."""

    def __init__(self, message: str = "موجودیت مورد نظر در Provider پیدا نشد."):
        super().__init__(message, retryable=False)


class ProviderValidationError(ProviderError):
    """ورودی نامعتبر یا رد شده توسط Provider (مثلاً ظرفیت پر است)."""

    def __init__(self, message: str = "درخواست توسط Provider رد شد."):
        super().__init__(message, retryable=False)
