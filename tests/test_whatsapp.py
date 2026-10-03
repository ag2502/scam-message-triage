import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from scam_triage import whatsapp
from scam_triage.api import app

SECRET = "test-secret"
client = TestClient(app)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRET)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setattr(whatsapp, "seen", whatsapp._SeenIds())
    sent = []
    monkeypatch.setattr(whatsapp, "send_text", lambda pid, to, body, reply_to=None: sent.append((pid, to, body, reply_to)))
    return sent


def _post(payload: dict, secret: str = SECRET):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhooks/whatsapp", content=body, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})


def _message(text: str | None = None, msg_id: str = "wamid.1", mtype: str = "text") -> dict:
    msg = {"from": "5511999990000", "id": msg_id, "timestamp": "1759490000", "type": mtype}
    if text is not None:
        msg["text"] = {"body": text}
    return {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [{"field": "messages", "value": {
        "messaging_product": "whatsapp", "metadata": {"display_phone_number": "15550000000", "phone_number_id": "PNID"},
        "messages": [msg]}}]}]}


def test_verify_handshake():
    ok = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"})
    assert ok.status_code == 200 and ok.text == "42"
    bad = client.get("/webhooks/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "42"})
    assert bad.status_code == 403


def test_scam_message_gets_verdict_as_quoted_reply(env):
    r = _post(_message("Hi mum, new number! Send R$900 by Pix urgently, can't talk now"))
    assert r.status_code == 200 and r.json()["handled"] == 1
    pid, to, body, reply_to = env[0]
    assert (pid, to, reply_to) == ("PNID", "5511999990000", "wamid.1")
    assert "RISK" in body and "What to do" in body


def test_bad_signature_rejected(env):
    assert _post(_message("hello"), secret="wrong").status_code == 403
    assert env == []


def test_retries_are_deduplicated(env):
    _post(_message("Pay your toll at ezpass-pay.top"))
    _post(_message("Pay your toll at ezpass-pay.top"))
    assert len(env) == 1


def test_greeting_and_non_text(env):
    _post(_message("hi", msg_id="a"))
    _post(_message(None, msg_id="b", mtype="image"))
    assert env[0][2] == whatsapp.WELCOME
    assert env[1][2] == whatsapp.NON_TEXT


def test_status_callbacks_are_ignored(env):
    payload = _message("x")
    del payload["entry"][0]["changes"][0]["value"]["messages"]
    payload["entry"][0]["changes"][0]["value"]["statuses"] = [{"id": "wamid.1", "status": "delivered"}]
    assert _post(payload).json()["handled"] == 0
    assert env == []
