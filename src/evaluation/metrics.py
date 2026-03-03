"""Deterministic metrics used by the offline benchmarking harness."""

from __future__ import annotations

from collections import Counter
from typing import Iterable


def _mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def exercise_macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    if not labels:
        return 0.0

    f1s: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        f1s.append(f1)
    return _mean(f1s)


def rep_count_mae(y_true: list[float], y_pred: list[float]) -> float:
    if not y_true or not y_pred:
        return 0.0
    return _mean(abs(float(t) - float(p)) for t, p in zip(y_true, y_pred))


def tempo_mae_s(
    y_true: list[tuple[float, float, float, float]],
    y_pred: list[tuple[float, float, float, float]],
) -> float:
    if not y_true or not y_pred:
        return 0.0
    errors: list[float] = []
    for gt, pred in zip(y_true, y_pred):
        for g, p in zip(gt, pred):
            errors.append(abs(float(g) - float(p)))
    return _mean(errors)


def angle_mae_deg(
    y_true: list[dict[str, float]],
    y_pred: list[dict[str, float]],
) -> float:
    if not y_true or not y_pred:
        return 0.0
    errors: list[float] = []
    for gt, pred in zip(y_true, y_pred):
        for key in sorted(set(gt.keys()) & set(pred.keys())):
            errors.append(abs(float(gt[key]) - float(pred[key])))
    return _mean(errors)


def compensation_f1(
    y_true: list[set[str]],
    y_pred: list[set[str]],
) -> float:
    if not y_true or not y_pred:
        return 0.0
    tp = fp = fn = 0
    for gt_set, pred_set in zip(y_true, y_pred):
        tp += len(gt_set & pred_set)
        fp += len(pred_set - gt_set)
        fn += len(gt_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0


def label_distribution(labels: list[str]) -> dict[str, int]:
    return dict(Counter(labels))

