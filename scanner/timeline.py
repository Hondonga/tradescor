"""Chronological ICT event timeline helpers."""

from __future__ import annotations


def build_analysis_timeline(
    zones: dict[str, object],
    order_blocks: dict[str, object],
    setup_status: str,
    bias: str,
    levels: dict[str, object] | None = None,
    current_price: float | None = None,
    current_time=None,
    levels_mode: str = "hidden",
) -> list[dict[str, object]]:
    """Create newest-first analysis events for the current chart only."""
    events: list[dict[str, object]] = []

    htf_fvg = zones.get("htf_fvg") or {}
    liquidity = zones.get("liquidity_zone") or {}
    mss = zones.get("mss") or {}
    ifvg = zones.get("ifvg") or {}
    order_block = order_blocks.get("nearest") or {}

    if htf_fvg:
        events.append(
            _event(
                htf_fvg.get("end_time"),
                "HTF FVG detected",
                htf_fvg.get("type", bias),
                f"{htf_fvg.get('type', '').title()} higher-timeframe FVG is active near price.",
                current_time,
            )
        )

    if liquidity:
        events.append(
            _event(
                liquidity.get("time"),
                "Liquidity sweep detected",
                liquidity.get("direction", bias),
                f"{liquidity.get('type', 'Liquidity').title()} liquidity swept at {liquidity.get('swept_level')}.",
                current_time,
            )
        )

    if mss:
        events.append(
            _event(
                mss.get("time"),
                "MSS confirmed",
                mss.get("direction", bias),
                f"{mss.get('direction', '').title()} market structure shift confirmed.",
                current_time,
            )
        )

    if order_block:
        events.append(
            _event(
                order_block.get("confirmed_time"),
                "Order block detected",
                order_block.get("direction", bias),
                order_block.get("label", "Order block detected."),
                current_time,
            )
        )

    if ifvg:
        events.append(
            _event(
                ifvg.get("end_time"),
                "IFVG detected",
                ifvg.get("type", bias),
                f"{ifvg.get('type', '').title()} IFVG entry zone detected.",
                current_time,
            )
        )

    if _target_reached(levels, current_price, bias, "tp2", levels_mode):
        events.append(
            _event(current_time, "TP2 reached", bias, f"Price reached TP2 at {levels.get('tp2')}.", current_time)
        )

    if _target_reached(levels, current_price, bias, "tp1", levels_mode):
        events.append(
            _event(current_time, "TP1 reached", bias, f"Price reached TP1 at {levels.get('tp1')}.", current_time)
        )

    if setup_status in {"VALID SETUP", "ENTRY READY"}:
        events.append(_event(current_time, "Entry ready", bias, f"{bias} setup is valid.", current_time))
    elif setup_status == "INVALIDATED":
        events.append(_event(current_time, "Setup invalidated", bias, "The current setup sequence is invalidated.", current_time))
    else:
        events.append(
            _event(
                current_time,
                "Setup waiting",
                bias,
                f"{setup_status}: waiting for the next required confirmation.",
                current_time,
            )
        )

    return sorted(events, key=lambda event: event["sort_time"], reverse=True)


def _target_reached(
    levels: dict[str, object] | None,
    current_price: float | None,
    bias: str,
    target_key: str,
    levels_mode: str,
) -> bool:
    if levels_mode != "final" or not levels or current_price is None:
        return False

    target = levels.get(target_key)
    if target is None:
        return False

    if bias == "LONG":
        return float(current_price) >= float(target)
    if bias == "SHORT":
        return float(current_price) <= float(target)
    return False


def _event(
    time_value,
    event_type: str,
    direction,
    explanation: str,
    fallback_time=None,
) -> dict[str, object]:
    time_text = str(time_value or fallback_time or "Current")
    direction_text = str(direction or "neutral").upper()

    return {
        "time": time_text,
        "event_type": event_type,
        "direction": direction_text,
        "explanation": explanation,
        "title": event_type,
        "detail": explanation,
        "sort_time": time_text,
    }
