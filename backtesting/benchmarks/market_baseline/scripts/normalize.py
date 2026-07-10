"""Normalization helpers for the market baseline benchmark."""

from __future__ import annotations

import math


EPSILON = 0.001


def clamp_probability(value: float | None, epsilon: float = EPSILON) -> float | None:
    if value is None:
        return None
    return max(epsilon, min(1.0 - epsilon, float(value)))


def brier(p_pred: float, outcome: float) -> float:
    p = clamp_probability(p_pred)
    y = float(outcome)
    return round((p - y) ** 2, 6)


def log_loss(p_pred: float, outcome: float) -> float:
    p = clamp_probability(p_pred)
    y = float(outcome)
    return round(-(y * math.log(p) + (1.0 - y) * math.log(1.0 - p)), 6)


def midpoint(low: float | None, high: float | None) -> float | None:
    if low is None or high is None:
        return None
    return round((float(low) + float(high)) / 2.0, 6)


def relative_probability(numerator: float | None, denominator_other: float | None) -> float | None:
    if numerator is None or denominator_other is None:
        return None
    total = float(numerator) + float(denominator_other)
    if total <= 0:
        return None
    return round(float(numerator) / total, 6)


def scaled_squared_error(prediction: float, outcome: float, scale: float) -> float:
    if scale <= 0:
        raise ValueError("scale must be positive")
    return round(((float(prediction) - float(outcome)) / scale) ** 2, 6)


def abs_error(prediction: float, outcome: float) -> float:
    return round(abs(float(prediction) - float(outcome)), 6)

