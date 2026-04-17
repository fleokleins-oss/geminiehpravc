from __future__ import annotations

def estimate_slippage_bps(side: str, qty: float, mid: float, spread_bps: float, imb: float, vol_bps: float) -> float:
    if mid <= 0 or qty <= 0:
        return 0.0
    base = max(0.1, 0.5 * spread_bps)
    impact = 8.0 * (1.0 - min(1.0, abs(imb)))
    vol = min(8.0, 0.15 * vol_bps)
    side_penalty = 1.25 if ((side == "BUY" and imb < 0) or (side == "SELL" and imb > 0)) else 1.0
    return (base + impact + vol) * side_penalty

def apply_slippage(mid: float, side: str, slippage_bps: float) -> float:
    sign = 1.0 if side.upper() == "BUY" else -1.0
    return mid * (1.0 + sign * slippage_bps / 10000.0)
