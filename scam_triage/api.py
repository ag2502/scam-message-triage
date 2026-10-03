"""FastAPI service.

    uvicorn scam_triage.api:app --reload
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from scam_triage import __version__
from scam_triage.lexicons import SUPPORTED_LANGS
from scam_triage.reply import format_reply
from scam_triage.triage import get_model, triage
from scam_triage.whatsapp import router as whatsapp_router

MAX_CHARS = 4000

app = FastAPI(
    title="Scam-Message Triage",
    version=__version__,
    description="Forward a suspicious message; get a risk score, scam type, reasons and next steps.",
)
app.include_router(whatsapp_router)


class TriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS, description="The message to check")
    lang: Literal[SUPPORTED_LANGS] = "en"  # type: ignore[valid-type]


class TriageResponse(BaseModel):
    risk_score: float
    risk_level: Literal["low", "medium", "high"]
    scam_type: str
    scam_type_label: str
    type_confidence: float
    summary: str
    reasons: list[str]
    key_phrases: list[str]
    next_steps: list[str]
    lang: str
    model_version: str
    reply_text: str


@app.get("/health")
def health() -> dict:
    model = get_model("en")
    return {"status": "ok", "version": __version__, "model_version": model.meta.get("version"), "langs": SUPPORTED_LANGS}


@app.post("/v1/triage", response_model=TriageResponse)
def triage_endpoint(req: TriageRequest) -> TriageResponse:
    result = triage(req.text, lang=req.lang)
    return TriageResponse(**result.to_dict(), reply_text=format_reply(result))
