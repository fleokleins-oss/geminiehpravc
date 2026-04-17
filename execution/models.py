from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from typing import Deque, Optional, List, Tuple

@dataclass
class OrderBook:
    bids: List[Tuple[float, float]] = field(default_factory=list)
    asks: List[Tuple[float, float]] = field(default_factory=list)
    last_update_id: int = 0

    def best_bid(self):
        return self.bids[0] if self.bids else None

    def best_ask(self):
        return self.asks[0] if self.asks else None

@dataclass
class SymbolState:
    symbol: str
    book: OrderBook = field(default_factory=OrderBook)
    last_trade_price: float = 0.0
    last_trade_qty: float = 0.0
    last_trade_is_buyer_maker: bool = False
    trade_prices: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    trade_signed_qty: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    trade_times_ms: Deque[int] = field(default_factory=lambda: deque(maxlen=500))
    last_action_ms: int = 0
    position_qty: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl_usd: float = 0.0

@dataclass
class SymbolRules:
    tick_size: float = 0.01
    step_size: float = 0.0001
    min_qty: float = 0.0001
    min_notional: float = 5.0

@dataclass
class OrderIntent:
    symbol: str
    side: str
    quantity: float
    mode: str
    score: float
    reason: str
    order_type: str = "MARKET"
    limit_price: float | None = None
