"""Slow bounded expert updates applied only after closed outcomes."""

from __future__ import annotations


def update_weight(current: float, realized_r: float, *, outcome_closed: bool, learning_rate: float = 0.02) -> float:
    if not outcome_closed:
        return max(.70, min(1.10, current))
    bounded_result = max(-2.0, min(2.0, float(realized_r)))
    return round(max(.70, min(1.10, current + learning_rate * bounded_result)), 4)
