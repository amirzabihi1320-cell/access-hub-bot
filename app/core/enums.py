"""
تمام Enumهای مشترک پروژه اینجا تعریف می‌شوند تا در models/services/handlers
یکسان استفاده شوند و رشته‌های Magic String در کد پخش نشود.
"""
import enum


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    WAITING_ADMIN = "WAITING_ADMIN"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class WalletTransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    PURCHASE = "PURCHASE"
    REFUND = "REFUND"
    BONUS = "BONUS"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"
    WITHDRAWAL = "WITHDRAWAL"
    TOURNAMENT_ENTRY = "TOURNAMENT_ENTRY"
    TOURNAMENT_PRIZE = "TOURNAMENT_PRIZE"


class DepositRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductType(str, enum.Enum):
    FIXED = "FIXED"
    VARIABLE_QUANTITY = "VARIABLE_QUANTITY"
    SUBSCRIPTION = "SUBSCRIPTION"
    GIFT_CODE = "GIFT_CODE"


class DeliveryType(str, enum.Enum):
    MANUAL = "MANUAL"
    CODE = "CODE"
    API = "API"
    TELEGRAM = "TELEGRAM"


class InventoryCodeStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    INVALID = "INVALID"


class AdminRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    FINANCE = "FINANCE"
    SUPPORT = "SUPPORT"
    ORDERS = "ORDERS"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER = "WAITING_USER"
    CLOSED = "CLOSED"


class MessageCategory(str, enum.Enum):
    """برای Message Manager - تعیین می‌کند پیام حذف/edit شود یا باقی بماند."""
    TEMPORARY = "TEMPORARY"
    IMPORTANT = "IMPORTANT"
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"
    DELIVERY = "DELIVERY"
    SYSTEM = "SYSTEM"


class MembershipRequirement(str, enum.Enum):
    ALL = "ALL"
    PURCHASE_ONLY = "PURCHASE_ONLY"
    BOT_USE_ONLY = "BOT_USE_ONLY"
    DISABLED = "DISABLED"


# ---------- Provider Engine / VPN Engine (فاز Provider) ----------


class VPNPanelType(str, enum.Enum):
    """
    نوع پنل VPN. هر مقدار باید در app/providers/registry.py به یک
    کلاس Provider concrete نگاشت شده باشد. اضافه‌کردن پنل جدید یعنی:
    ۱) یک مقدار اینجا اضافه کن، ۲) یک Provider در app/providers/vpn/
    بنویس، ۳) در registry.py ثبتش کن. بدون تغییر بقیه‌ی سیستم.
    """
    MARZBAN = "MARZBAN"
    SANAEI = "SANAEI"  # اسکلت آماده - پیاده‌سازی کامل در فاز بعد


class VPNPanelStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class HealthStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class VPNServiceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


# ---------- Crypto Payment Engine (TRON/Tronado - ماژول اضافه) ----------


class PaymentProviderType(str, enum.Enum):
    """
    نوع Payment Provider خارجی (غیر از درگاه ریالی/کارت‌به‌کارت داخلی).
    اضافه‌کردن Provider جدید = ۱) مقدار اینجا، ۲) کلاس در app/providers/payment/،
    ۳) ثبت در registry.py. دقیقاً همان الگوی VPNPanelType.
    """
    TRONADO = "TRONADO"


class PaymentProviderStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class CryptoCurrency(str, enum.Enum):
    """بند ۳ سند: هر ارز Ledger مستقل خودش را دارد."""
    TRX = "TRX"
    TON = "TON"  # فعلاً فقط تعریف Enum - Wallet/Provider آن در فاز بعد پیاده می‌شود


class CryptoWalletTxType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"
    CONVERSION_OUT = "CONVERSION_OUT"  # فاز بعد (TRX -> TON)
    CONVERSION_IN = "CONVERSION_IN"    # فاز بعد
    WITHDRAWAL = "WITHDRAWAL"


class CryptoDepositStatus(str, enum.Enum):
    """State Machine سفارش واریز TRX (بند ۱۷ سند - نسخه‌ی محدود به Deposit)."""
    CREATED = "CREATED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
