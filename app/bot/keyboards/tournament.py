from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

METRIC_LABELS = {
    "REFERRALS": "👥 بیشترین دعوت موفق",
    "PURCHASES": "🛍 بیشترین خرید تکمیل‌شده",
}


def tournaments_list_keyboard(tournaments) -> InlineKeyboardMarkup:
    rows = []
    for t in tournaments:
        rows.append([InlineKeyboardButton(text=f"🏆 {t.title}", callback_data=f"tournament:view:{t.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tournament_detail_keyboard(tournament_id: int, joined: bool) -> InlineKeyboardMarkup:
    rows = []
    if not joined:
        rows.append([InlineKeyboardButton(text="✅ شرکت در تورنومنت", callback_data=f"tournament:join:{tournament_id}")])
    rows.append([InlineKeyboardButton(text="📊 جدول رده‌بندی", callback_data=f"tournament:board:{tournament_id}")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="tournament:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tournament_board_back_keyboard(tournament_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"tournament:view:{tournament_id}")]]
    )


# ---------- ادمین ----------


def admin_tournament_metric_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:tournament:metric:{key}")]
        for key, label in METRIC_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_tournaments_keyboard(tournaments) -> InlineKeyboardMarkup:
    rows = []
    status_mark = {"ACTIVE": "🟢", "ENDED": "🟠", "SETTLED": "⚪️", "CANCELLED": "🔴"}
    for t in tournaments:
        mark = status_mark.get(t.status, "⚪️")
        rows.append([InlineKeyboardButton(text=f"{mark} {t.title}", callback_data=f"admin:tournament:view:{t.id}")])
    rows.append([InlineKeyboardButton(text="➕ تورنومنت جدید", callback_data="admin:tournament:add")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_tournament_detail_keyboard(tournament) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📊 جدول رده‌بندی", callback_data=f"admin:tournament:board:{tournament.id}")]]
    if tournament.status == "ACTIVE":
        rows.append([InlineKeyboardButton(text="⏹ پایان دادن الان", callback_data=f"admin:tournament:end:{tournament.id}")])
        rows.append([InlineKeyboardButton(text="❌ لغو و بازگشت ورودی‌ها", callback_data=f"admin:tournament:cancel:{tournament.id}")])
    if tournament.status in ("ACTIVE", "ENDED"):
        rows.append(
            [InlineKeyboardButton(text="🏆 تعیین برنده و پرداخت جایزه", callback_data=f"admin:tournament:settle:{tournament.id}")]
        )
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:tournaments")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
