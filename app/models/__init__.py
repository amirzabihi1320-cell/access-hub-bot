"""
تمام مدل‌ها اینجا import می‌شوند تا Alembic هنگام autogenerate
همه‌ی جدول‌ها را ببیند. هر مدل جدید در فازهای بعد اینجا اضافه شود.
"""
from app.models.user import User  # noqa: F401
from app.models.wallet import Wallet, WalletTransaction  # noqa: F401
from app.models.setting import Setting, TextTemplate  # noqa: F401
from app.models.required_channel import RequiredChannel  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.deposit_request import DepositRequest  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.inventory_code import InventoryCode  # noqa: F401
