# 🌐 Access Hub | مارکت دیجیتال

ربات فروشگاهی ماژولار برای فروش محصولات دیجیتال داخل تلگرام.

## وضعیت فعلی (تا پایان فاز ۵)

تا اینجا پیاده‌سازی شده:

- ✅ ساختار پروژه (Handlers / Services / Repositories / Models جدا از هم)
- ✅ Config با Pydantic Settings + Generic Settings System از دیتابیس
- ✅ اتصال Async به PostgreSQL با SQLAlchemy 2.x + Alembic
- ✅ `/start` + منوی اصلی + Membership Check + حساب کاربری/Referral (فاز ۱)
- ✅ دسته‌بندی‌ها + محصولات Fixed/Variable Quantity + Pricing Engine (فاز ۲)
- ✅ کیف پول کامل + Wallet Ledger + شارژ دستی + تأیید/رد ادمین (فاز ۳)
- ✅ سفارش‌ها + پرداخت آنی با کیف پول + تحویل دستی توسط ادمین (فاز ۴)
- ✅ **پنل ادمین (`/admin`) کامل: داشبورد، محصولات (افزودن/قیمت/فعال-غیرفعال)،
  دسته‌بندی‌ها (افزودن/فعال-غیرفعال)، تنظیمات، عضویت اجباری، شارژهای در
  انتظار، سفارش‌های در انتظار (فاز ۵)**
- ✅ متن‌های ربات به حداقل ضروری کاهش پیدا کرد (بدون شلوغی اضافه)
- ✅ Dockerfile + docker-compose، تست‌های SQLite in-memory

هنوز پیاده نشده: Role-based Permission چندسطحی برای ادمین‌ها (فعلاً هر
ADMIN_IDS دسترسی کامل دارد)، کوپن/رفرال reward/VIP (فاز ۶)، تیکت/
Broadcast/Audit Log (فاز ۷)، Telegram Stars (فاز ۸).

---

## 🚀 نحوه اجرا (Local / Development)

### ۱. کلون و نصب وابستگی‌ها

```bash
cd access-hub-bot
python -m venv venv
source venv/bin/activate   # ویندوز: venv\Scripts\activate
pip install -r requirements.txt
```

### ۲. تنظیم Environment Variables

```bash
cp .env.example .env
```

سپس مقادیر واقعی را داخل `.env` بگذار:

```
BOT_TOKEN=توکن ربات از BotFather
BOT_USERNAME=AccessHubMarketBot
DATABASE_URL=postgresql+asyncpg://access_hub:access_hub@localhost:5432/access_hub
MAIN_CHANNEL_ID=@AccessHubMarket
REPORT_CHANNEL_ID=@AccessHubReport
ADMIN_IDS=آیدی_عددی_خودت
```

> برای گرفتن آیدی عددی تلگرامت، به ربات `@userinfobot` پیام بده.

### ۳. بالا آوردن دیتابیس (با Docker)

```bash
docker compose up -d db
```

### ۴. اجرای Migration اول

```bash
alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

### ۵. اجرای ربات

```bash
python -m app.main
```

اگه همه‌چیز درست باشه، به ربات توی تلگرام `/start` بزن و باید منوی اصلی رو ببینی.

---

## 🐳 اجرا با Docker Compose کامل (بات + دیتابیس)

```bash
docker compose up --build
```

---

## 🧪 اجرای تست‌ها

```bash
pytest -v
```

---

## 📂 ساختار پروژه

```
app/
  bot/
    handlers/      → فقط ورودی/خروجی تلگرام (بدون منطق تجاری)
    keyboards/      → کیبوردهای Inline
    middlewares/    → مثل Maintenance Mode, Membership Check (فاز بعد)
    states/         → FSM states
  services/         → تمام منطق تجاری اینجاست (UserService, WalletService, ...)
  repositories/     → دسترسی به دیتابیس (در فازهای بعد تکمیل می‌شود)
  models/           → مدل‌های SQLAlchemy
  schemas/          → Pydantic schemas برای اعتبارسنجی ورودی/خروجی
  core/             → Enumها و ابزارهای مشترک
  config/           → خواندن Environment Variables
  database/         → اتصال دیتابیس (Base, Session)
  main.py           → نقطه ورود ربات
alembic/            → مایگریشن‌های دیتابیس
tests/              → تست‌ها
```

قانون طلایی معماری: **هیچ منطق تجاری داخل Handler نوشته نمی‌شود.**
Handler فقط پیام تلگرام را می‌گیرد → Service را صدا می‌زند → نتیجه را نمایش می‌دهد.

---

## 🗺 فازهای بعدی

| فاز | محتوا |
|---|---|
| ~~۱~~ | ~~Membership Check کامل + User Account Page~~ ✅ |
| ~~۲~~ | ~~Categories + Products (Fixed & Variable Quantity) + Pricing Engine~~ ✅ |
| ~~۳~~ | ~~Wallet Service کامل + Ledger + Manual Deposit + تأیید/رد ادمین~~ ✅ |
| ~~۴~~ | ~~Order Service + Wallet Payment + Delivery Engine (Manual/Code)~~ ✅ |
| ~~۵~~ | ~~Admin Panel (`/admin`): داشبورد، محصولات، دسته‌بندی‌ها، تنظیمات، عضویت اجباری~~ ✅ |
| ۶ | Coupon + Referral + VIP |
| ۷ | Support/Ticket System + Broadcast + Audit Log |
| ۸ | Telegram Stars Payment + تست‌های کامل + Deployment نهایی |

هر فاز رو جدا درخواست بده تا با همین کیفیت و کامل تحویل بدم.

---

## ⚠️ نکات امنیتی مهم

- هیچ‌وقت `BOT_TOKEN` یا `DATABASE_URL` را داخل کد یا Git commit نکن — همیشه در `.env`
- فایل `.env` در `.gitignore` قرار دارد
- تمام عملیات مالی باید از `WalletService` عبور کنند (در فاز ۳) تا Ledger درست ثبت شود


### Shop button customization
- Category and product buttons support `primary` (blue), `success` (green), and `danger` (red).
- Admin can change each item's button color from its management screen.
- Button layout remains per-item: full-width (1) or two columns (2).
- Shop category/product buttons use an enlarged two-line visual style so their rendered size is substantially larger on Telegram mobile; Telegram does not expose pixel width/height for InlineKeyboardButton.
