from fastapi.testclient import TestClient

from scam_triage.api import app
from scam_triage.cli import main

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_triage_flags_family_scam():
    r = client.post("/v1/triage", json={"text": "Hi mum, this is my new number. Can you send £400 urgently? Can't talk"})
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] in {"medium", "high"}
    assert body["scam_type"] == "family_impersonation"
    assert body["reasons"] and body["next_steps"]
    assert "RISK" in body["reply_text"]


def test_triage_passes_ordinary_chat():
    body = client.post("/v1/triage", json={"text": "Running 10 min late, order me a coffee?"}).json()
    assert body["risk_level"] == "low"
    assert body["scam_type"] == "legit"


def test_validation_errors():
    assert client.post("/v1/triage", json={"text": ""}).status_code == 422
    assert client.post("/v1/triage", json={"text": "hi", "lang": "xx"}).status_code == 422
    assert client.post("/v1/triage", json={"text": "x" * 5000}).status_code == 422


def test_cli_json(capsys):
    assert main(["Your parcel is held, pay the £1.99 fee at royalmail-redelivery.top", "--json"]) == 0
    assert '"risk_level"' in capsys.readouterr().out
