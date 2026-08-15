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
