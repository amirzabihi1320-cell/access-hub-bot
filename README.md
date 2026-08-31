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

### 🔌 Provider Engine / VPN Engine (شروع‌شده)

- ✅ `app/providers/` — رابط انتزاعی مشترک Provider (`BaseProvider`) و VPN
  (`BaseVPNProvider`) + `registry.py` برای افزودن پنل جدید بدون تغییر Core.
- ✅ **Marzban Provider کامل** (`app/providers/vpn/marzban.py`): Auth،
  Health Check، Create/Get/Modify/Delete/Revoke/Enable/Disable User، با
  Refresh خودکار توکن و نگاشت خطاها به پیام کاربرپسند (Provider اصلی هرگز
  مستقیم به کاربر نشان داده نمی‌شود).
- ✅ مدل‌های `VPNPanel` (چند پنل هم‌زمان، اولویت، Health کش‌شده) و
  `VPNService` (سرویس تحویل‌شده به کاربر) + Migration `0016_vpn_engine`.
- ✅ `VPNProvisioningService` — Smart Panel Selection با Failover خودکار
  بین پنل‌ها (بند ۱۵ سند).
- ✅ مدیریت کامل پنل‌ها از پنل ادمین تلگرام (افزودن/تست اتصال/فعال-غیرفعال/حذف)
  بدون نیاز به تغییر کد. Credential پنل‌ها با Fernet رمزنگاری می‌شود
  (`PANEL_ENCRYPTION_KEY` در `.env` - جزئیات نهایی مدیریت کلید در فاز
  مستقل Security مشخص می‌شود).
- ✅ **اتصال کامل به Order Engine (بند ۵۷: Payment → VPN Automation):**
  هر محصول می‌تواند از صفحه‌ی مدیریت محصول به «تحویل خودکار VPN» تنظیم شود
  (حجم ترافیک GB + مدت روز، بند ۲۰: Traffic Packages). بعد از پرداخت موفق
  (کیف‌پول/کد تخفیف/Token — هر سه مسیر)، `try_auto_deliver_vpn` خودکار
  کاربر را روی پنل مناسب می‌سازد و سفارش COMPLETED می‌شود؛ اگر همه‌ی
  پنل‌ها Fail شدند، بدون نمایش خطای فنی به کاربر، سفارش در همان صف تحویل
  دستی موجود (`WAITING_ADMIN`) می‌ماند (بند ۲۷، ۵۸).
- ✅ «🔐 سرویس‌های VPN من» برای کاربر (بند ۱۸: مشاهده‌ی سرویس‌ها + دریافت
  دوباره‌ی لینک/کانفیگ).
- ✅ **Retry با Exponential Backoff** (بند ۲۸): خطای موقت (قطعی اتصال/۵xx)
  تا ۳ بار روی همان پنل با تاخیر تصاعدی (۱، ۲، ۴ ثانیه) دوباره امتحان
  می‌شود؛ خطای غیرموقت (Auth/Validation) بدون اتلاف وقت مستقیم به پنل
  بعدی می‌رود (بند ۲۷: Alternative Provider).
- ✅ **Auto-Renew کامل** (بند ۱۹): دکمه‌ی «🔄 تمدید» در «سرویس‌های VPN من» -
  همان اکانت روی همان پنل تمدید می‌شود (لینک/کانفیگ قبلی معتبر می‌ماند)،
  مبلغ طبق قیمت *فعلیِ* محصول از کیف‌پول کسر می‌شود و اگر تمدید روی پنل
  شکست بخورد، مبلغ بلافاصله و به‌صورت یک تراکنش Refund مستقل (نه ویرایش)
  برگردانده می‌شود.
- ✅ **Sanaei/3x-UI Provider کامل** (`app/providers/vpn/sanaei.py`، بند ۱۳):
  Login با Session Cookie، Create/Get/Modify/Delete/Enable/Disable/Reset
  Traffic کلاینت. برخلاف Marzban که هر کاربر Username یکتا دارد، در
  X-UI هر کلاینت با UUID داخل یک Inbound شناسایی می‌شود؛ برای سازگاری
  با رابط عمومی VPN Engine، UUID به‌صورت Deterministic (uuid5) از روی
  همان username تولید می‌شود - نیازی به ذخیره‌ی جداگانه نیست. هر پنل
  می‌تواند یک `default_inbound_id` داشته باشد (اختیاری - در غیر این
  صورت اولین Inbound فعال خودکار انتخاب می‌شود).
- ⏳ هنوز نیست: Worker/Queue واقعی برای Retry پس‌زمینه‌ای (فعلاً Retry
  همزمان و داخل همان درخواست کاربر انجام می‌شود)، Revoke UUID برای
  X-UI (معماری متفاوت این پنل اجازه‌ی Revoke ساده نمی‌دهد - نیاز به
  Delete+Recreate در سطح بالاتر دارد).

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

## Automatic TRX payment (Tronado)

Access Hub includes a Tronado payment adapter for automatic wallet deposits. See
`PAYMENT_SETUP.md` for the required environment variables and webhook setup.
The integration is server-to-server and verifies Tronado's signed IPN before crediting
an internal wallet. It does not attempt to control `@tronadorobot` as a Telegram user/bot.
