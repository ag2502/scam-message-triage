"""Evaluation focused on the operating regime that matters: very few false alarms.

A triage bot that cries wolf on real bank alerts gets ignored, so the headline
metrics are recall and precision at fixed low false-positive rates. Thresholds
are always picked on the validation split and *then* applied to test data, so
the reported FPRs are what a deployment would actually see.

Precision depends on how common scams are among the messages people forward,
so it is also reported at several assumed prevalences:
    precision(p) = TPR * p / (TPR * p + FPR * (1 - p))
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold

from scam_triage.model import TriageModel, threshold_at_fpr

FPR_TARGETS = (0.001, 0.005, 0.01, 0.05)
PREVALENCES = (0.01, 0.1, 0.5)


def precision_at_prevalence(tpr: float, fpr: float, p: float) -> float | None:
    denom = tpr * p + fpr * (1 - p)
    return None if denom == 0 else tpr * p / denom


def operating_point(scores: np.ndarray, y: np.ndarray, threshold: float) -> dict:
    pred = scores >= threshold
    tp, fp = int(np.sum(pred & (y == 1))), int(np.sum(pred & (y == 0)))
    fn, tn = int(np.sum(~pred & (y == 1))), int(np.sum(~pred & (y == 0)))
    tpr = tp / max(tp + fn, 1)
    fpr = fp / max(fp + tn, 1)
    return {
        "threshold": round(float(threshold), 6),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "recall": round(tpr, 4),
        "fpr": round(fpr, 5),
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        "precision_at_prevalence": {
            str(p): (round(v, 4) if (v := precision_at_prevalence(tpr, fpr, p)) is not None else None)
            for p in PREVALENCES
        },
    }


def binary_report(scores: np.ndarray, y: np.ndarray, thresholds: dict[str, float]) -> dict:
    out = {"n": int(len(y)), "n_scam": int(y.sum()), "n_legit": int((y == 0).sum())}
    if 0 < y.sum() < len(y):
        out["roc_auc"] = round(float(roc_auc_score(y, scores)), 4)
        out["pr_auc"] = round(float(average_precision_score(y, scores)), 4)
    out["operating_points"] = {name: operating_point(scores, y, t) for name, t in thresholds.items()}
    return out


def type_report(model: TriageModel, rows: list[dict]) -> dict:
    """Scam-type accuracy on true scams whose label is in the taxonomy."""
    known = set(model.type_clf.classes_)
    rows = [r for r in rows if r["is_scam"] and r["label"] in known]
    if not rows:
        return {}
    y = [r["label"] for r in rows]
    classes, probs = model.type_probs([r["text"] for r in rows])
    pred = [classes[i] for i in probs.argmax(1)]
    labels = sorted(known)
    per_class = f1_score(y, pred, labels=labels, average=None, zero_division=0)
    return {
        "n": len(rows),
        "accuracy": round(accuracy_score(y, pred), 4),
        "macro_f1": round(f1_score(y, pred, labels=labels, average="macro", zero_division=0), 4),
        "per_class_f1": {lab: round(float(f), 4) for lab, f in zip(labels, per_class)},
        "labels": labels,
        "confusion": confusion_matrix(y, pred, labels=labels).tolist(),
    }


def val_thresholds(model: TriageModel, val: list[dict]) -> dict[str, float]:
    scores = model.risk_scores([r["text"] for r in val])
    legit = scores[np.array([r["is_scam"] for r in val]) == 0]
    ths = {f"fpr@{t:g}": threshold_at_fpr(legit, t) for t in FPR_TARGETS}
    ths |= {f"model_{lvl}": t for lvl, t in model.thresholds.items()}
    return ths


def evaluate_split(model: TriageModel, rows: list[dict], thresholds: dict[str, float]) -> dict:
    scores = model.risk_scores([r["text"] for r in rows])
    y = np.array([r["is_scam"] for r in rows])
    rep = {"binary": binary_report(scores, y, thresholds), "type": type_report(model, rows)}
    # False-positive rate by data source (e.g. synthetic legit vs. real UCI ham).
    hi = thresholds["model_high"]
    rep["fpr_by_source_at_high"] = {
        src: round(float(np.mean(scores[[i for i, r in enumerate(rows) if r["source"] == src and not r["is_scam"]]] >= hi)), 5)
        for src in sorted({r["source"] for r in rows if not r["is_scam"]})
    }
    rep["errors"] = errors(rows, scores, model)
    return rep


def errors(rows: list[dict], scores: np.ndarray, model: TriageModel, limit: int = 25) -> dict:
    med = model.thresholds["medium"]
    classes, probs = model.type_probs([r["text"] for r in rows])
    missed, false_alarms, wrong_type = [], [], []
    for r, s, p in zip(rows, scores, probs):
        pred_type = classes[int(p.argmax())]
        item = {"id": r["id"], "label": r["label"], "score": round(float(s), 4), "pred_type": pred_type, "text": r["text"]}
        if r["is_scam"] and s < med:
            missed.append(item)
        elif not r["is_scam"] and s >= med:
            false_alarms.append(item)
        elif r["is_scam"] and r["label"] in classes and pred_type != r["label"]:
            wrong_type.append(item)
    key = lambda d: d["score"]  # noqa: E731
    return {
        "missed_scams": sorted(missed, key=key)[:limit],
        "false_alarms": sorted(false_alarms, key=key, reverse=True)[:limit],
        "wrong_type": wrong_type[:limit],
    }


def grouped_cv(rows: list[dict], lang: str, n_splits: int = 5, C: float = 10.0, type_C: float = 1.0) -> dict:
    """Template-grouped CV: each fold holds out whole templates, estimating generalization to new phrasings."""
    groups = [r["template_id"] or r["id"] for r in rows]
    y = np.array([r["is_scam"] for r in rows])
    folds = []
    for tr_idx, te_idx in GroupKFold(n_splits=n_splits).split(rows, y, groups):
        tr = [rows[i] for i in tr_idx]
        te = [rows[i] for i in te_idx]
        m = TriageModel.train(tr, te, lang=lang, c_grid=(C,), type_c_grid=(type_C,))
        s = m.risk_scores([r["text"] for r in te])
        yt = y[te_idx]
        th = threshold_at_fpr(s[yt == 0], 0.01)
        folds.append({
            "roc_auc": roc_auc_score(yt, s),
            "pr_auc": average_precision_score(yt, s),
            "recall_at_1pct_fpr": float(np.mean(s[yt == 1] >= th)),
            "type_macro_f1": type_report(m, te).get("macro_f1", float("nan")),
        })
    return {
        k: {"mean": round(float(np.mean([f[k] for f in folds])), 4), "std": round(float(np.std([f[k] for f in folds])), 4)}
        for k in folds[0]
    } | {"n_splits": n_splits, "note": "recall@1%FPR uses a threshold set on each held-out fold (ranking quality)"}

