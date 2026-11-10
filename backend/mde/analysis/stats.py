from __future__ import annotations

import math


def stat(value, reason=None):
    if value is None:
        return {"value": None, "reason": reason}
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return {"value": None, "reason": reason or "invalid_value"}
    if not math.isfinite(numeric):
        return {"value": None, "reason": reason or "non_finite_value"}
    return {"value": numeric, "reason": reason}
