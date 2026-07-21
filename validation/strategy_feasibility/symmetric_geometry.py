"""Symmetric trade geometry.

To isolate *direction* from *geometry*, every control uses identical risk and
reward distances, mirrored around entry. Stop and target are equidistant in R,
so any edge that appears cannot be an artifact of asymmetric target selection
(the exact distortion that inflated JDBR's first fade result from +0.02R to
+0.16R).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Geometry:
    direction: int    # +1 long / -1 short
    entry: float
    stop: float
    target: float
    risk: float
    rr: float


def build_symmetric_geometry(entry: float, atr: float, direction: int,
                             risk_atr: float = 1.0, rr: float = 1.5) -> Geometry:
    """Fixed-risk, fixed-RR geometry. Same magnitude for every direction."""
    risk = risk_atr * atr
    stop = entry - direction * risk
    target = entry + direction * (rr * risk)
    return Geometry(direction=direction, entry=entry, stop=stop, target=target, risk=risk, rr=rr)
