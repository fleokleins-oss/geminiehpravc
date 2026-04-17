from __future__ import annotations
import asyncio
import json
import os
import time
from pathlib import Path

from .config import EngineConfig
from .models import SymbolState
from .microstructure import mid_price, spread_bps, imbalance, realized_vol_bps
from .signals import SignalModel, load_best_gene
from .slippage import estimate_slippage_bps, apply_slippage
from .binance_ws import stream_updates, install_uvloop_if_available
from .binance_rest import BinanceSpotRestClient

class PaperBroker:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log = self.output_dir / "paper_fills.jsonl"

    def submit(self, intent: dict, state: SymbolState):
        stats = intent["stats"]
        slip = estimate_slippage_bps(intent["side"], intent["qty"], stats["mid"], stats["spread_bps"], stats["imbalance"], stats["vol_bps"])
        fill = apply_slippage(stats["mid"], intent["side"], slip)
        signed = intent["qty"] if intent["side"] == "BUY" else -intent["qty"]
        state.position_qty += signed
        event = {
            "ts_ms": int(time.time() * 1000),
            "mode": "paper",
            "symbol": intent["symbol"],
            "side": intent["side"],
            "qty": intent["qty"],
            "fill_price": fill,
            "slippage_bps": slip,
            "score": intent["score"],
            "reason": intent.get("reason", ""),
        }
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "
")
        return event

class LiveBroker:
    def __init__(self, client: BinanceSpotRestClient, test_order: bool = False):
        self.client = client
        self.test_order = test_order

    def submit(self, intent: dict, state: SymbolState, rules: dict):
        symbol = intent["symbol"].upper()
        side = intent["side"].upper()
        qty = intent["qty"]
        mid = intent["stats"]["mid"]
        qty = max(rules["min_qty"], (qty // rules["step_size"]) * rules["step_size"])
        if qty * mid < rules["min_notional"]:
            qty = max(qty, rules["min_notional"] / max(mid, 1e-9))
        if intent.get("mode") == "maker":
            if side == "BUY":
                price = mid * 0.999
            else:
                price = mid * 1.001
            return self.client.place_order(symbol, side, qty, order_type="LIMIT", price=price)
        return self.client.place_order(symbol, side, qty, order_type="MARKET")

class ExecutionEngine:
    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)
        self.states = {s.upper(): SymbolState(symbol=s.upper()) for s in cfg.symbols}
        self.rules_cache = {}
        self.last_gene_refresh = 0.0
        self.signal_model = SignalModel(load_best_gene(cfg.gene_path))
        self.api_key = os.environ.get("BINANCE_API_KEY")
        self.api_secret = os.environ.get("BINANCE_API_SECRET")
        base_url = cfg.testnet_base_url if cfg.mode == "testnet" else cfg.live_base_url
        self.rest = BinanceSpotRestClient(self.api_key, self.api_secret, base_url=base_url, test_mode=(cfg.mode == "testnet"))
        self.paper = PaperBroker(cfg.output_dir)
        self.live = LiveBroker(self.rest, test_order=(cfg.mode == "testnet"))
        self.event_log = cfg.output_dir / "engine_events.jsonl"

    def log(self, payload: dict):
        payload["ts_ms"] = int(time.time() * 1000)
        with self.event_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "
")

    def rules(self, symbol: str):
        symbol = symbol.upper()
        if symbol not in self.rules_cache:
            try:
                self.rules_cache[symbol] = self.rest.symbol_rules(symbol)
            except Exception:
                self.rules_cache[symbol] = {"tick_size": 0.01, "step_size": 0.0001, "min_qty": 0.0001, "min_notional": 5.0}
        return self.rules_cache[symbol]

    def refresh_gene_if_needed(self):
        now = time.time()
        if now - self.last_gene_refresh < 10:
            return
        self.signal_model = SignalModel(load_best_gene(self.cfg.gene_path))
        self.last_gene_refresh = now

    def update_trade(self, sym: str, data: dict):
        st = self.states[sym]
        p = float(data.get("p") or data.get("price") or 0.0)
        q = float(data.get("q") or data.get("qty") or 0.0)
        bm = bool(data.get("m", data.get("isBuyerMaker", False)))
        signed = -q if bm else q
        st.last_trade_price = p
        st.last_trade_qty = q
        st.last_trade_is_buyer_maker = bm
        st.trade_prices.append(p)
        st.trade_signed_qty.append(signed)
        st.trade_times_ms.append(int(data.get("E") or data.get("T") or time.time() * 1000))

    def update_book(self, sym: str, data: dict):
        st = self.states[sym]
        bids = []
        asks = []
        for p, q in data.get("bids", data.get("b", []))[: self.cfg.depth_level]:
            p = float(p); q = float(q)
            if q > 0:
                bids.append((p, q))
        for p, q in data.get("asks", data.get("a", []))[: self.cfg.depth_level]:
            p = float(p); q = float(q)
            if q > 0:
                asks.append((p, q))
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])
        st.book.bids = bids
        st.book.asks = asks
        st.book.last_update_id = int(data.get("u") or data.get("U") or data.get("lastUpdateId") or 0)

    def maybe_trade(self, sym: str):
        st = self.states[sym]
        now_ms = int(time.time() * 1000)
        if now_ms - st.last_action_ms < self.cfg.cooldown_ms:
            return None
        intent, stats = self.signal_model.intent(sym, st, self.cfg.budget_usd)
        if intent is None:
            return None

        intent["reason"] = (
            f"score={intent['score']:.3f} thr={stats['threshold']:.3f} "
            f"imb={stats['imbalance']:.3f} micro={stats['micro_edge_bps']:.2f}bps "
            f"flow={stats['flow']:.3f} vol={stats['vol_bps']:.2f}"
        )
        st.last_action_ms = now_ms

        if self.cfg.mode == "paper":
            result = self.paper.submit(intent, st)
        else:
            result = self.live.submit(intent, st, self.rules(sym))

        self.log({"symbol": sym, "intent": intent, "stats": stats, "result": result})
        return result

    async def run(self, duration_min: float = 0.0):
        install_uvloop_if_available()

        if self.cfg.mode == "live" and (not self.api_key or not self.api_secret):
            raise RuntimeError("BINANCE_API_KEY and BINANCE_API_SECRET are required for live mode")

        end_time = time.time() + duration_min * 60.0 if duration_min and duration_min > 0 else None

        async for upd in stream_updates(
            self.cfg.symbols,
            self.cfg.market_ws_base_url,
            depth_level=self.cfg.depth_level,
            depth_speed=self.cfg.depth_speed,
            time_unit=self.cfg.time_unit,
        ):
            if end_time and time.time() > end_time:
                break

            stream = (upd.stream or "").lower()
            data = upd.data
            if "@trade" in stream:
                sym = (data.get("s") or stream.split("@", 1)[0]).upper()
                if sym in self.states:
                    self.update_trade(sym, data)
                    self.maybe_trade(sym)
            elif "@depth" in stream:
                sym = (data.get("s") or stream.split("@", 1)[0]).upper()
                if sym in self.states:
                    self.update_book(sym, data)
                    self.maybe_trade(sym)

            self.refresh_gene_if_needed()
