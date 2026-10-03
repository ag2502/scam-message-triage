"""Explainable triage model.

Two linear models over the same features:
  * risk model: binary scam-vs-legit logistic regression -> risk score in [0, 1]
  * type model: multinomial logistic regression over scam types, trained on scams only

Features are word n-grams (readable, used for evidence), char n-grams (robust to
typos and obfuscation) and the binary signals from `scam_triage.signals`.
Linear weights make every score decomposable into the phrases and signals that
drove it, which is what the plain-language explanation is built from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score

from scam_triage import __version__
from scam_triage.signals import AMOUNT_RE, PHONE_RE, URL_RE, normalize, signal_ids, signal_vector
from scam_triage.taxonomy import LEGIT

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
SIGNAL_WEIGHT = 1.0  # scale of the binary signal block relative to tf-idf features
TARGET_FPRS = {"high": 0.01, "medium": 0.05}


def preprocess(text: str) -> str:
    """Normalize and mask volatile tokens so the model learns patterns, not specific URLs/numbers."""
    text = normalize(text).lower()
    text = URL_RE.sub(" __url__ ", text)
    text = PHONE_RE.sub(" __phone__ ", text)
    text = AMOUNT_RE.sub(" __amount__ ", text)
    text = re.sub(r"\d+", "0", text)
    return re.sub(r"\s+", " ", text).strip()


class Featurizer:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r"(?u)\b[\w']+\b|__\w+__")
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=60000)
        self.signal_names = list(signal_ids(lang))

    def _signals(self, texts: list[str]) -> sparse.csr_matrix:
        return sparse.csr_matrix(np.array([signal_vector(t, self.lang) for t in texts], dtype=float) * SIGNAL_WEIGHT)

    def fit_transform(self, texts: list[str]) -> sparse.csr_matrix:
        pre = [preprocess(t) for t in texts]
        return sparse.hstack([self.word.fit_transform(pre), self.char.fit_transform(pre), self._signals(texts)]).tocsr()

    def transform(self, texts: list[str]) -> sparse.csr_matrix:
        pre = [preprocess(t) for t in texts]
        return sparse.hstack([self.word.transform(pre), self.char.transform(pre), self._signals(texts)]).tocsr()

    @property
    def n_word(self) -> int:
        return len(self.word.vocabulary_)

    @property
    def n_char(self) -> int:
        return len(self.char.vocabulary_)

    def feature_names(self) -> list[str]:
        return [
            *self.word.get_feature_names_out(),
            *(f"char:{c}" for c in self.char.get_feature_names_out()),
            *(f"signal:{s}" for s in self.signal_names),
        ]


def threshold_at_fpr(scores_legit: np.ndarray, fpr: float) -> float:
    """Smallest threshold whose false-positive rate on legit scores is <= fpr."""
    s = np.sort(scores_legit)[::-1]
    k = int(np.floor(fpr * len(s)))
    return float(s[k]) + 1e-9 if k < len(s) else 0.0


@dataclass
class TriageModel:
    lang: str
    featurizer: Featurizer
    risk_clf: LogisticRegression
    type_clf: LogisticRegression
    thresholds: dict[str, float]
    meta: dict = field(default_factory=dict)

    # ---- training -------------------------------------------------------
    @classmethod
    def train(cls, train: list[dict], val: list[dict], lang: str = "en", c_grid=(0.3, 1.0, 3.0, 10.0)) -> "TriageModel":
        feat = Featurizer(lang)
        X_tr = feat.fit_transform([r["text"] for r in train])
        X_va = feat.transform([r["text"] for r in val])
        y_tr = np.array([r["is_scam"] for r in train])
        y_va = np.array([r["is_scam"] for r in val])

        best_risk = max(
            (cls._fit_risk(X_tr, y_tr, c) for c in c_grid),
            key=lambda m: average_precision_score(y_va, m.predict_proba(X_va)[:, 1]),
        )

        scam_tr = [i for i, r in enumerate(train) if r["is_scam"]]
        scam_va = [i for i, r in enumerate(val) if r["is_scam"]]
        t_tr = np.array([train[i]["label"] for i in scam_tr])
        t_va = np.array([val[i]["label"] for i in scam_va])
        best_type = max(
            (LogisticRegression(C=c, max_iter=3000).fit(X_tr[scam_tr], t_tr) for c in c_grid),
            key=lambda m: f1_score(t_va, m.predict(X_va[scam_va]), average="macro"),
        )

        val_scores = best_risk.predict_proba(X_va)[:, 1]
        thresholds = {lvl: threshold_at_fpr(val_scores[y_va == 0], fpr) for lvl, fpr in TARGET_FPRS.items()}
        meta = {
            "version": __version__,
            "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "risk_C": best_risk.C,
            "type_C": best_type.C,
            "n_train": len(train),
            "n_val": len(val),
            "target_fprs": TARGET_FPRS,
            "sources": sorted({r["source"] for r in train}),
        }
        return cls(lang, feat, best_risk, best_type, thresholds, meta)

    @staticmethod
    def _fit_risk(X, y, c: float) -> LogisticRegression:
        return LogisticRegression(C=c, max_iter=3000, class_weight="balanced").fit(X, y)

    # ---- inference ------------------------------------------------------
    def risk_scores(self, texts: list[str]) -> np.ndarray:
        return self.risk_clf.predict_proba(self.featurizer.transform(texts))[:, 1]

    def type_probs(self, texts: list[str]) -> tuple[list[str], np.ndarray]:
        return list(self.type_clf.classes_), self.type_clf.predict_proba(self.featurizer.transform(texts))

    def level(self, score: float) -> str:
        if score >= self.thresholds["high"]:
            return "high"
        if score >= self.thresholds["medium"]:
            return "medium"
        return "low"

    def contributions(self, text: str) -> list[tuple[str, float]]:
        """Per-feature contribution (x_i * w_i) to the risk logit, largest first, non-zero only."""
        x = self.featurizer.transform([text]).tocoo()
        w = self.risk_clf.coef_[0]
        names = self._names()
        contrib = [(names[j], float(v * w[j])) for j, v in zip(x.col, x.data)]
        return sorted(contrib, key=lambda kv: kv[1], reverse=True)

    def _names(self) -> list[str]:
        if not hasattr(self, "_name_cache"):
            self._name_cache = self.featurizer.feature_names()
        return self._name_cache

    # ---- persistence ----------------------------------------------------
    def save(self, path: Path | None = None) -> Path:
        path = path or default_model_path(self.lang)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.__dict__.pop("_name_cache", None)
        joblib.dump(self, path, compress=3)
        return path

    @staticmethod
    def load(path: Path | None = None, lang: str = "en") -> "TriageModel":
        return joblib.load(path or default_model_path(lang))


def default_model_path(lang: str = "en") -> Path:
    return MODEL_DIR / lang / "triage.joblib"


__all__ = ["TriageModel", "Featurizer", "preprocess", "threshold_at_fpr", "LEGIT"]
