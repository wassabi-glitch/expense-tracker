from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def normalize_telegram_language(lang_code: str | None) -> str:
    raw = (lang_code or "").strip().lower()
    if raw.startswith("ru"):
        return "ru"
    if raw.startswith("uz"):
        return "uz"
    return "en"


@dataclass(frozen=True)
class TelegramMessageCatalog:
    strings: dict[str, dict[str, str]]

    def t(self, key: str, lang: str, **params: Any) -> str:
        bucket = self.strings.get(key, {})
        template = bucket.get(lang) or bucket.get("en") or ""
        return template.format(**params)


CATALOG = TelegramMessageCatalog(
    strings={
        "id_response": {
            "en": (
                "Your Telegram IDs:\n"
                "- chat_id: <b>{chat_id}</b>\n"
                "- user_id: <b>{user_id}</b>\n\n"
                "Set <b>TELEGRAM_ADMIN_CHAT_IDS</b> to your <b>user_id</b> (or chat_id) and restart the API."
            ),
            "ru": (
                "Ваши Telegram ID:\n"
                "- chat_id: <b>{chat_id}</b>\n"
                "- user_id: <b>{user_id}</b>\n\n"
                "Укажите <b>TELEGRAM_ADMIN_CHAT_IDS</b> = ваш <b>user_id</b> (или chat_id) и перезапустите API."
            ),
            "uz": (
                "Telegram IDlaringiz:\n"
                "- chat_id: <b>{chat_id}</b>\n"
                "- user_id: <b>{user_id}</b>\n\n"
                "<b>TELEGRAM_ADMIN_CHAT_IDS</b> ga o'zingizning <b>user_id</b> (yoki chat_id) ni yozing va API'ni qayta ishga tushiring."
            ),
        },
        "start_no_order": {
            "en": "Send your receipt screenshot as a photo.\n\nTip: send <b>/id</b> to see your Telegram numeric IDs.",
            "ru": "Отправьте скриншот чека как фото.\n\nПодсказка: отправьте <b>/id</b>, чтобы увидеть числовые Telegram ID.",
            "uz": "Chek skrinshotini foto sifatida yuboring.\n\nMaslahat: Telegram raqamli ID'laringizni ko'rish uchun <b>/id</b> yozing.",
        },
        "order_not_found": {
            "en": "Order not found: <b>{order_code}</b>",
            "ru": "Buyurtma topilmadi: <b>{order_code}</b>",
            "uz": "Buyurtma topilmadi: <b>{order_code}</b>",
        },
        "order_already_processed": {
            "en": "Order already processed: <b>{order_code}</b>",
            "ru": "Buyurtma allaqachon qayta ishlangan: <b>{order_code}</b>",
            "uz": "Buyurtma allaqachon qayta ishlangan: <b>{order_code}</b>",
        },
        "order_linked": {
            "en": "Order <b>{order_code}</b> linked. Now send your receipt screenshot as a photo.",
            "ru": "Buyurtma <b>{order_code}</b> bog'landi. Endi chek skrinshotini foto qilib yuboring.",
            "uz": "Buyurtma <b>{order_code}</b> bog'landi. Endi chek skrinshotini foto qilib yuboring.",
        },
        "order_missing_retry": {
            "en": "Could not find your order. Please open the Telegram link from the app again and then resend the receipt.",
            "ru": "Buyurtmangizni topib bo'lmadi. Iltimos, ilovadan Telegram havolasini qayta oching va chekning rasmini yana yuboring.",
            "uz": "Buyurtmangizni topib bo'lmadi. Iltimos, ilovadan Telegram havolasini qayta oching va chekning rasmini yana yuboring.",
        },
        "receipt_received": {
            "en": "Thanks! Receipt received for <b>{order_code}</b>. We'll review it and activate Premium if approved.",
            "ru": "Rahmat! <b>{order_code}</b> uchun chek qabul qilindi. Tekshiramiz va tasdiqlansa Premium yoqiladi.",
            "uz": "Rahmat! <b>{order_code}</b> uchun chek qabul qilindi. Tekshiramiz va tasdiqlansa Premium yoqiladi.",
        },
        "approved_user": {
            "en": "✅ Approved! Premium activated for order <b>{order_code}</b>.",
            "ru": "✅ Tasdiqlandi! <b>{order_code}</b> buyurtmasi uchun Premium yoqildi.",
            "uz": "✅ Tasdiqlandi! <b>{order_code}</b> buyurtmasi uchun Premium yoqildi.",
        },
        "rejected_user": {
            "en": "❌ Rejected. If this is a mistake, please contact support with order <b>{order_code}</b>.",
            "ru": "❌ Rad etildi. Xatolik bo'lsa, <b>{order_code}</b> buyurtma ID bilan bog'laning.",
            "uz": "❌ Rad etildi. Xatolik bo'lsa, <b>{order_code}</b> buyurtma ID bilan bog'laning.",
        },
        "not_authorized": {
            "en": "Not authorized.",
            "ru": "Ruxsat yo'q.",
            "uz": "Ruxsat yo'q.",
        },
        "approved_admin": {
            "en": "Approved.",
            "ru": "Tasdiqlandi.",
            "uz": "Tasdiqlandi.",
        },
        "rejected_admin": {
            "en": "Rejected.",
            "ru": "Rad etildi.",
            "uz": "Rad etildi.",
        },
    }
)

