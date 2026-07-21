"""Quality checks for the active ICT order block."""

from __future__ import annotations


def evaluate_order_block(
    order_blocks: dict[str, object],
    direction: str | None,
    current_price: float,
) -> dict[str, object]:
    """Rate the nearest active block using direction, status, and confluence."""
    block = order_blocks.get("nearest") or {}
    if not block:
        return {"present": False, "valid": False, "quality": "Missing", "score": 0, "reasons": [], "block": {}}

    normalized = _direction(direction)
    block_direction = str(block.get("direction", "")).lower()
    status = str(block.get("status", "active")).lower()
    reasons: list[str] = []
    score = 0

    if status == "active":
        score += 35
        reasons.append("The block remains active.")
    if normalized and block_direction == normalized:
        score += 30
        reasons.append("The block aligns with higher-timeframe direction.")
    if block.get("confluence"):
        score += 20
        reasons.append("The block overlaps higher-timeframe imbalance.")
    if _inside(current_price, block):
        score += 15
        reasons.append("Price is currently interacting with the block.")

    valid = score >= 60 and status == "active"
    quality = "Strong" if score >= 80 else "Valid" if valid else "Weak"
    return {
        "present": True,
        "valid": valid,
        "quality": quality,
        "score": score,
        "reasons": reasons,
        "block": block,
    }


def _inside(price: float, block: dict[str, object]) -> bool:
    top = block.get("top_price")
    bottom = block.get("bottom_price")
    return top is not None and bottom is not None and float(bottom) <= price <= float(top)


def _direction(value: str | None) -> str | None:
    text = str(value or "").lower()
    if text in {"bullish", "long"}:
        return "bullish"
    if text in {"bearish", "short"}:
        return "bearish"
    return None
