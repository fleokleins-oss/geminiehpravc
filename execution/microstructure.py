from __future__ import annotations
from math import log
from .models import OrderBook, SymbolState

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def best_bid_ask(book: OrderBook):
    bid = book.best_bid()
    ask = book.best_ask()
    if not bid or not ask:
        return None
    return bid[0], bid[1], ask[0], ask[1]

def mid_price(book: OrderBook) -> float:
    b = best_bid_ask(book)
    if not b:
        return 0.0
    bid_p, _, ask_p, _ = b
    return (bid_p + ask_p) / 2.0

def spread_bps(book: OrderBook) -> float:
    b = best_bid_ask(book)
    if not b:
        return 0.0
    bid_p, _, ask_p, _ = b
    mid = (bid_p + ask_p) / 2.0
    return ((ask_p - bid_p) / mid * 10000.0) if mid > 0 else 0.0

def microprice(book: OrderBook) -> float:
    b = best_bid_ask(book)
    if not b:
        return 0.0
    bid_p, bid_q, ask_p, ask_q = b
    denom = bid_q + ask_q
    return (ask_p * bid_q + bid_p * ask_q) / denom if denom > 0 else (bid_p + ask_p) / 2.0

def imbalance(book: OrderBook) -> float:
    b = best_bid_ask(book)
    if not b:
        return 0.0
    _, bid_q, _, ask_q = b
    denom = bid_q + ask_q
    return (bid_q - ask_q) / denom if denom > 0 else 0.0

def trade_flow_ema(state: SymbolState, alpha: float = 0.18) -> float:
    ema = 0.0
    for x in state.trade_signed_qty:
        ema = alpha * x + (1 - alpha) * ema
    return ema

def realized_vol_bps(state: SymbolState) -> float:
    prices = list(state.trade_prices)
    if len(prices) < 5:
        return 0.0
    rets = []
    for i in range(1, len(prices)):
        p0, p1 = prices[i-1], prices[i]
        if p0 > 0 and p1 > 0:
            rets.append(abs(log(p1 / p0)) * 10000.0)
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / max(1, len(rets) - 1)
    return var ** 0.5

def quantize_floor(v: float, step: float) -> float:
    if step <= 0:
        return v
    return (v // step) * step
