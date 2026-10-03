import numpy as np
import pytest

from scam_triage.model import TriageModel, preprocess, threshold_at_fpr
from scam_triage.synth import generate
from scam_triage.taxonomy import SCAM_TYPE_IDS
from scam_triage.triage import triage


def test_preprocess_masks_volatile_tokens():
    out = preprocess("Pay $4.15 at https://ezpass-x.top/pay or call +1 (555) 013-2847, ref 99812")
    assert "__url__" in out and "__phone__" in out and "__amount__" in out
    assert "99812" not in out


def test_threshold_at_fpr():
    legit = np.linspace(0, 1, 101)
    t = threshold_at_fpr(legit, 0.05)
    assert np.mean(legit >= t) <= 0.05


@pytest.fixture(scope="module")
def small_model():
    rows = generate(seed=7, scam_per_label=48, legit_total=400)
    train = [r for r in rows if r["split"] == "train"]
    val = [r for r in rows if r["split"] != "train"]
    return TriageModel.train(train, val, c_grid=(1.0,))


def test_small_model_trains_and_round_trips(small_model, tmp_path):
    assert set(small_model.type_clf.classes_) == set(SCAM_TYPE_IDS)
    assert small_model.thresholds["high"] >= small_model.thresholds["medium"]
    path = small_model.save(tmp_path / "m.joblib")
    loaded = TriageModel.load(path)
    texts = ["Your parcel is held, pay the redelivery fee at usps-pay.top", "see you at lunch"]
    assert np.allclose(loaded.risk_scores(texts), small_model.risk_scores(texts))


def test_triage_result_shape(small_model):
    r = triage("Hi mum, new number! Can you send $500 by Zelle urgently? Can't call", model=small_model)
    assert r.risk_level in {"medium", "high"}
    assert r.scam_type == "family_impersonation"
    assert r.reasons and r.next_steps
    assert all("__" not in p for p in r.key_phrases)


def test_low_risk_hides_context_reasons(small_model):
    r = triage("Thanks for dinner! Sent you $25 on Venmo", model=small_model)
    if r.risk_level == "low":
        assert r.scam_type == "legit" and r.key_phrases == []
