"""WhatsApp Cloud API bot: forward a suspicious message, get a verdict back.

Webhook endpoints (register the URL in the Meta app dashboard):
  GET  /webhooks/whatsapp  verification handshake (hub.challenge)
  POST /webhooks/whatsapp  incoming messages, verified with X-Hub-Signature-256

Configuration (environment variables):
  WHATSAPP_VERIFY_TOKEN    token you choose and enter in the Meta dashboard
  WHATSAPP_APP_SECRET      app secret, used to verify webhook signatures (required)
  WHATSAPP_ACCESS_TOKEN    system-user access token used to send replies
  WHATSAPP_GRAPH_VERSION   Graph API version (default v23.0)

Message text is never logged.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from collections import OrderedDict
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from scam_triage.reply import format_reply
from scam_triage.triage import triage_text

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])

WELCOME = (
    "👋 Hi! I check messages for scams.\n\n"
    "*Forward me* any suspicious WhatsApp or SMS message (or paste its text) and I'll tell you how risky it looks, "
    "what kind of scam it might be and what to do next.\n\n"
    "_I only read text for now. I can't check images, voice notes or calls._"
)
NON_TEXT = "I can only check text right now. Please paste the text of the message you received."
GREETINGS = {"hi", "hello", "hey", "help", "start", "menu", "oi", "olá", "hola"}
MAX_CHARS = 4000


@dataclass(frozen=True)
class Settings:
    verify_token: str | None
    app_secret: str | None
    access_token: str | None
    graph_version: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            os.getenv("WHATSAPP_VERIFY_TOKEN"),
            os.getenv("WHATSAPP_APP_SECRET"),
            os.getenv("WHATSAPP_ACCESS_TOKEN"),
            os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0"),
        )


class _SeenIds:
    """Bounded memory of processed message ids. Meta retries webhooks, so replies must be idempotent."""

    def __init__(self, maxlen: int = 5000):
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._maxlen = maxlen

    def add(self, msg_id: str) -> bool:
        """Return True if `msg_id` is new."""
        if msg_id in self._ids:
            return False
        self._ids[msg_id] = None
        if len(self._ids) > self._maxlen:
            self._ids.popitem(last=False)
        return True


seen = _SeenIds()


def valid_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def send_text(phone_number_id: str, to: str, body: str, reply_to: str | None = None) -> None:
    s = Settings.from_env()
    if not s.access_token:
        log.error("WHATSAPP_ACCESS_TOKEN not set; cannot send reply")
        return
    payload: dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }
    if reply_to:
        payload["context"] = {"message_id": reply_to}
    url = f"https://graph.facebook.com/{s.graph_version}/{phone_number_id}/messages"
    try:
        r = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {s.access_token}"}, timeout=10)
        if r.status_code >= 400:
            log.error("WhatsApp send failed: %s %s", r.status_code, r.text[:300])
    except httpx.HTTPError as exc:
        log.error("WhatsApp send error: %s", exc)


def reply_for(message: dict) -> str:
    """The text to send back for one incoming WhatsApp message object."""
    if message.get("type") != "text":
        return NON_TEXT
    text = (message.get("text") or {}).get("body", "").strip()
    if not text or text.lower().strip("!.? ") in GREETINGS:
        return WELCOME
    return format_reply(triage_text(text[:MAX_CHARS]))


@router.get("", response_class=PlainTextResponse)
def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> str:
    expected = Settings.from_env().verify_token
    if mode == "subscribe" and expected and hmac.compare_digest(token, expected):
        return challenge
    raise HTTPException(status_code=403, detail="verification failed")


@router.post("")
async def receive(request: Request, background: BackgroundTasks) -> dict:
    s = Settings.from_env()
    if not s.app_secret:
        raise HTTPException(status_code=503, detail="WHATSAPP_APP_SECRET not configured")
    body = await request.body()
    if not valid_signature(s.app_secret, body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="bad signature")

    payload = await request.json()
    handled = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for msg in value.get("messages", []):  # absent for delivery/read status callbacks
                msg_id, sender = msg.get("id"), msg.get("from")
                if not (msg_id and sender and phone_number_id) or not seen.add(msg_id):
                    continue
                background.add_task(_answer, phone_number_id, sender, msg, msg_id)
                handled += 1
    # Always 200 quickly; Meta retries on errors/timeouts.
    return {"status": "ok", "handled": handled}


def _answer(phone_number_id: str, sender: str, msg: dict, msg_id: str) -> None:
    send_text(phone_number_id, sender, reply_for(msg), reply_to=msg_id)
