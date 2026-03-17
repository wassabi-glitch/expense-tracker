import logging
from typing import Any, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _bot_token() -> Optional[str]:
    token = settings.telegram_bot_token
    if token is None:
        return None
    return token.get_secret_value() or None


def _api_url(method: str) -> str:
    token = _bot_token()
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    return f"https://api.telegram.org/bot{token}/{method}"


async def send_message(
    chat_id: int,
    text: str,
    *,
    reply_markup: Optional[dict[str, Any]] = None,
) -> None:
    token = _bot_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set; skipping telegram send_message")
        return

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(_api_url("sendMessage"), json=payload)


async def copy_message(
    to_chat_id: int,
    from_chat_id: int,
    message_id: int,
) -> None:
    token = _bot_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set; skipping telegram copy_message")
        return

    payload = {
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(_api_url("copyMessage"), json=payload)


async def answer_callback_query(callback_query_id: str, text: str = "") -> None:
    token = _bot_token()
    if not token:
        return

    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(_api_url("answerCallbackQuery"), json=payload)
