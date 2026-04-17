from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass
from .microstructure import mid_price, spread_bps, microprice, imbalance, trade_flow_ema, realized_vol_bps

def load_best_gene(path: Path | None = None) -> dict:
    path = path or Path("shared_genes/genes.json")
    if not path.exists():
        return {"feature": "micro", "window": 60, "threshold": 1.25}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return {"feature": "micro", "window": 60, "threshold": 1.25}
        genome = item.get("genome", item)
        return {
            "feature": genome.get("f", genome.get("feature", "micro")),
            "window": int(genome.get("w", genome.get("window", 60))),
            "threshold": float(genome.get("threshold", 1.25)),
        }
    except Exception:
        return {"feature": "micro", "window": 60, "threshold": 1.25}

@dataclass
class SignalModel:
    gene: dict

    def score(self, state):
        if not state.book.best_bid() or not state.book.best_ask():
            return {"score": 0.0, "mid": 0.0, "threshold": 1.25}
        mid = mid_price(state.book)
        spr = spread_bps(state.book)
        mic = microprice(state.book)
        imb = imbalance(state.book)
        flow = trade_flow_ema(state)
        vol = realized_vol_bps(state)

        feature = str(self.gene.get("feature", "micro")).lower()
        threshold = float(self.gene.get("threshold", 1.25))

        micro_edge_bps = (mic - mid) / mid * 10000.0 if mid > 0 else 0.0

        base = 0.0
        if feature in ("micro", "price"):
            base += 1.2 * micro_edge_bps
        if feature in ("imb", "imbalance"):
            base += 2.3 * imb
        if feature == "flow":
            base += 0.08 * flow
        if feature == "volume":
            base += 0.02 * vol

        score = base - 0.12 * spr
        return {
            "score": float(score),
            "mid": float(mid),
            "threshold": threshold,
            "spread_bps": float(spr),
            "imbalance": float(imb),
            "micro_edge_bps": float(micro_edge_bps),
            "flow": float(flow),
            "vol_bps": float(vol),
        }

    def intent(self, symbol: str, state, budget_usd: float):
        stats = self.score(state)
        if abs(stats["score"]) < stats["threshold"]:
            return None, stats
        side = "BUY" if stats["score"] > 0 else "SELL"
        qty = max(0.0001, budget_usd / max(stats["mid"], 1e-9))
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "score": stats["score"],
            "stats": stats,
            "mode": "taker" if abs(stats["score"]) > stats["threshold"] * 1.6 else "maker",
        }, stats
