"""FastAPI service.

    uvicorn scam_triage.api:app --reload
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

from scam_triage import __version__
from scam_triage.lexicons import SUPPORTED_LANGS
from scam_triage.reply import format_reply
from scam_triage.triage import get_model, triage_text, triage_thread
from scam_triage.whatsapp import router as whatsapp_router

MAX_CHARS = 4000

app = FastAPI(
    title="Scam-Message Triage",
    version=__version__,
    description="Forward a suspicious message; get a risk score, scam type, reasons and next steps.",
)
app.include_router(whatsapp_router)


class TriageRequest(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=MAX_CHARS,
                             description="The message to check (a pasted WhatsApp conversation is split automatically)")
    messages: list[str] | None = Field(None, min_length=1, max_length=20,
                                       description="A conversation, oldest first; the last message is judged in its light")
    lang: Literal[SUPPORTED_LANGS] = "en"  # type: ignore[valid-type]

    @model_validator(mode="after")
    def one_input(self):
        if (self.text is None) == (self.messages is None):
            raise ValueError("send exactly one of 'text' or 'messages'")
        if self.messages is not None and any(not m.strip() or len(m) > MAX_CHARS for m in self.messages):
            raise ValueError(f"messages must be non-empty and at most {MAX_CHARS} characters each")
        return self


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
    asks: list[str]
    cautions: list[str]
    thread_size: int
    from_context: bool
    reply_text: str


@app.get("/health")
def health() -> dict:
    model = get_model("en")
    return {"status": "ok", "version": __version__, "model_version": model.meta.get("version"), "langs": SUPPORTED_LANGS}


@app.post("/v1/triage", response_model=TriageResponse)
def triage_endpoint(req: TriageRequest) -> TriageResponse:
    result = triage_thread(req.messages, lang=req.lang) if req.messages else triage_text(req.text, lang=req.lang)
    return TriageResponse(**result.to_dict(), reply_text=format_reply(result))
