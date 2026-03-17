import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from calendar import monthrange

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from config import settings
from .. import models, oauth2, schemas
from ..session import get_db
from ..telegram import answer_callback_query, copy_message, send_message
from ..telegram_messages import CATALOG, normalize_telegram_language
from ..timezone import resolve_effective_timezone, now_in_tz

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)

PLAN_PRICES = {
    "BETA_MONTHLY": 11990,
    "BETA_YEARLY": 79990,
    "BETA_LIFETIME": 109990,
}

ORDER_CODE_RE = re.compile(r"\bORD-[A-Z0-9]+\b")


def _extract_order_code(text: str) -> str:
    match = ORDER_CODE_RE.search(text or "")
    return match.group(0) if match else ""


def _add_months_utc(base_utc: datetime, months: int, user_tz) -> datetime:
    local = base_utc.astimezone(user_tz)
    year = local.year + (local.month - 1 + months) // 12
    month = (local.month - 1 + months) % 12 + 1
    day = min(local.day, monthrange(year, month)[1])
    return local.replace(year=year, month=month, day=day).astimezone(timezone.utc)


def _add_years_utc(base_utc: datetime, years: int, user_tz) -> datetime:
    local = base_utc.astimezone(user_tz)
    year = local.year + years
    day = min(local.day, monthrange(year, local.month)[1])
    return local.replace(year=year, day=day).astimezone(timezone.utc)


def _apply_plan_to_user(user: models.User, plan_id: str) -> None:
    user_tz = resolve_effective_timezone(user_timezone=getattr(user, "timezone", None))
    now_utc = now_in_tz(user_tz).astimezone(timezone.utc)

    if plan_id == "BETA_MONTHLY":
        base = user.premium_expires_at if user.premium_expires_at and user.premium_expires_at > now_utc else now_utc
        user.premium_expires_at = _add_months_utc(base, 1, user_tz)
        user.is_premium = True
        return

    if plan_id == "BETA_YEARLY":
        base = user.premium_expires_at if user.premium_expires_at and user.premium_expires_at > now_utc else now_utc
        user.premium_expires_at = _add_years_utc(base, 1, user_tz)
        user.is_premium = True
        return

    if plan_id == "BETA_LIFETIME":
        user.is_premium = True
        user.premium_expires_at = None
        return


@router.post("/create-invoice", status_code=status.HTTP_201_CREATED, response_model=schemas.CreateInvoiceOut)
def create_invoice(
    payload: schemas.CreateInvoiceIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    plan_id = payload.plan_id
    if plan_id not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="payments.invalid_plan_id")

    amount = PLAN_PRICES[plan_id]
    order_code = f"ORD-{str(uuid.uuid4()).split('-')[0].upper()}"

    transaction = models.PaymentTransaction(
        user_id=current_user.id,
        order_code=order_code,
        plan_id=plan_id,
        amount=amount,
        currency="UZS",
        status=models.PaymentStatus.PENDING
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "order_code": transaction.order_code,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "plan_id": plan_id
    }

@router.post("/telegram-webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    telegram_secret: Optional[str] = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    expected_secret = settings.telegram_webhook_secret_token.get_secret_value() if settings.telegram_webhook_secret_token else ""
    if expected_secret and telegram_secret != expected_secret:
        raise HTTPException(status_code=401, detail="payments.telegram_webhook_unauthorized")

    payload = await request.json()
    
    # Log incoming webhook for debugging
    logger.info(f"Telegram webhook received: {payload}")
    
    admin_chat_ids = set(settings.telegram_admin_chat_id_list)

    if "message" in payload:
        message = payload["message"]
        chat_id = int(message.get("chat", {}).get("id"))
        from_user_id = int(message.get("from", {}).get("id"))
        lang = normalize_telegram_language(message.get("from", {}).get("language_code"))
        text = (message.get("text") or "").strip()

        if text in {"/id", "/whoami", "id"}:
            background_tasks.add_task(
                send_message,
                chat_id,
                CATALOG.t("id_response", lang, chat_id=chat_id, user_id=from_user_id),
            )
            return {"status": "ok"}

        if text.startswith("/start"):
            start_payload = text.split(maxsplit=1)[1].strip() if " " in text else ""
            order_code = _extract_order_code(start_payload)
            if not order_code:
                background_tasks.add_task(
                    send_message,
                    chat_id,
                    CATALOG.t("start_no_order", lang),
                )
                return {"status": "ok"}

            tx = db.query(models.PaymentTransaction).filter_by(order_code=order_code).first()
            if not tx:
                background_tasks.add_task(
                    send_message,
                    chat_id,
                    CATALOG.t("order_not_found", lang, order_code=order_code),
                )
                return {"status": "ok"}

            if tx.status != models.PaymentStatus.PENDING:
                background_tasks.add_task(
                    send_message,
                    chat_id,
                    CATALOG.t("order_already_processed", lang, order_code=order_code),
                )
                return {"status": "ok"}

            tx.telegram_chat_id = chat_id
            tx.telegram_user_id = from_user_id
            tx.telegram_language_code = lang
            db.commit()

            background_tasks.add_task(
                send_message,
                chat_id,
                CATALOG.t("order_linked", lang, order_code=order_code),
            )
            return {"status": "linked"}

        if message.get("photo"):
            message_id = int(message.get("message_id"))
            caption = message.get("caption") or ""
            order_code = _extract_order_code(caption)

            query = db.query(models.PaymentTransaction).filter(models.PaymentTransaction.status == models.PaymentStatus.PENDING)
            if order_code:
                query = query.filter(models.PaymentTransaction.order_code == order_code)
            else:
                query = query.filter(models.PaymentTransaction.telegram_chat_id == chat_id)

            tx = query.order_by(models.PaymentTransaction.created_at.desc()).first()
            if not tx:
                background_tasks.add_task(
                    send_message,
                    chat_id,
                    CATALOG.t("order_missing_retry", lang),
                )
                return {"status": "ok"}

            tx.telegram_chat_id = chat_id
            tx.telegram_user_id = from_user_id
            tx.telegram_language_code = lang
            tx.telegram_receipt_message_id = message_id
            tx.receipt_submitted_at = datetime.now(timezone.utc)
            db.commit()

            background_tasks.add_task(
                send_message,
                chat_id,
                CATALOG.t("receipt_received", lang, order_code=tx.order_code),
            )

            if admin_chat_ids:
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Approve", "callback_data": f"approve_{tx.order_code}"},
                            {"text": "❌ Reject", "callback_data": f"reject_{tx.order_code}"},
                        ]
                    ]
                }

                for admin_chat_id in admin_chat_ids:
                    background_tasks.add_task(copy_message, admin_chat_id, chat_id, message_id)
                    background_tasks.add_task(
                        send_message,
                        admin_chat_id,
                        (
                            f"Receipt submitted\n"
                            f"Order: <b>{tx.order_code}</b>\n"
                            f"Plan: <b>{tx.plan_id}</b>\n"
                            f"Amount: <b>{tx.amount} {tx.currency}</b>\n"
                            f"User ID: <b>{tx.user_id}</b>"
                        ),
                        reply_markup=keyboard,
                    )

            return {"status": "receipt_received"}

    if "callback_query" in payload:
        callback_query = payload["callback_query"]
        data = callback_query.get("data", "")
        callback_query_id = callback_query.get("id", "")
        from_user_id = int(callback_query.get("from", {}).get("id"))
        admin_lang = normalize_telegram_language(callback_query.get("from", {}).get("language_code"))

        if admin_chat_ids and from_user_id not in admin_chat_ids:
            if callback_query_id:
                background_tasks.add_task(
                    answer_callback_query,
                    callback_query_id,
                    CATALOG.t("not_authorized", admin_lang),
                )
            return {"status": "ignored"}
        
        if data.startswith("approve_"):
            order_code = data.split("_", 1)[1]
            tx = db.query(models.PaymentTransaction).filter_by(order_code=order_code).first()
            if tx and tx.status == models.PaymentStatus.PENDING:
                tx.status = models.PaymentStatus.COMPLETED
                user = tx.user

                _apply_plan_to_user(user, tx.plan_id)
                db.commit()

                if callback_query_id:
                    background_tasks.add_task(
                        answer_callback_query,
                        callback_query_id,
                        CATALOG.t("approved_admin", admin_lang),
                    )
                if tx.telegram_chat_id:
                    user_lang = tx.telegram_language_code or "en"
                    background_tasks.add_task(
                        send_message,
                        int(tx.telegram_chat_id),
                        CATALOG.t("approved_user", user_lang, order_code=tx.order_code),
                    )
                return {"status": "approved"}
                
        elif data.startswith("reject_"):
            order_code = data.split("_", 1)[1]
            tx = db.query(models.PaymentTransaction).filter_by(order_code=order_code).first()
            if tx and tx.status == models.PaymentStatus.PENDING:
                tx.status = models.PaymentStatus.REJECTED
                db.commit()
                if callback_query_id:
                    background_tasks.add_task(
                        answer_callback_query,
                        callback_query_id,
                        CATALOG.t("rejected_admin", admin_lang),
                    )
                if tx.telegram_chat_id:
                    user_lang = tx.telegram_language_code or "en"
                    background_tasks.add_task(
                        send_message,
                        int(tx.telegram_chat_id),
                        CATALOG.t("rejected_user", user_lang, order_code=tx.order_code),
                    )
                return {"status": "rejected"}
                
    return {"status": "ok"}
