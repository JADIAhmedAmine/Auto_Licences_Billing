from __future__ import annotations

from typing import Any, Dict, Optional


def _pct_change(new: int, prev: Optional[int]) -> float:
    if prev is None:
        return 0.0
    if prev == 0:
        return float("inf") if new > 0 else 0.0
    return abs(new - prev) / abs(prev)


def drift_audit(qty_new: int, qty_prev: Optional[int], warn_thr: float, crit_thr: float) -> Dict[str, Any]:
    pct = _pct_change(qty_new, qty_prev)

    if qty_prev is None:
        return {
            "status": "ok",
            "anomaly_score": 0.0,
            "reason": "Pas d'historique (première observation)",
            "pct_change": pct,
        }

    if pct >= crit_thr:
        return {
            "status": "critical",
            "anomaly_score": 0.95,
            "reason": f"Augmentation critique: {pct:.0%} vs M-1 ({qty_new} vs {qty_prev})",
            "pct_change": pct,
        }

    if pct >= warn_thr:
        return {
            "status": "warning",
            "anomaly_score": 0.75,
            "reason": f"Augmentation élevée: {pct:.0%} vs M-1 ({qty_new} vs {qty_prev})",
            "pct_change": pct,
        }

    return {
        "status": "ok",
        "anomaly_score": 0.05,
        "reason": "Consommation stable",
        "pct_change": pct,
    }
