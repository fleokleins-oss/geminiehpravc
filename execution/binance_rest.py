from __future__ import annotations
import hmac
import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def _request(url: str, method: str = "GET", headers: dict | None = None):
    req = Request(url, method=method, headers=headers or {})
    with urlopen(req, timeout=15) as resp:
        raw = resp.read()
        if raw[:1] in (b"{", b"["):
            return json.loads(raw.decode("utf-8"))
        return raw.decode("utf-8", errors="replace")

@dataclass
class BinanceSpotRestClient:
    api_key: str | None
    api_secret: str | None
    base_url: str
    recv_window: int = 5000
    test_mode: bool = False

    def public_get(self, path: str, params: dict | None = None):
        q = urlencode(params or {})
        url = f"{self.base_url}{path}" + (f"?{q}" if q else "")
        return _request(url, "GET")

    def signed_request(self, method: str, path: str, params: dict):
        if not self.api_key or not self.api_secret:
            raise RuntimeError("API key/secret required")
        params = dict(params)
        params.setdefault("recvWindow", self.recv_window)
        params.setdefault("timestamp", int(__import__("time").time() * 1000))
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key}
        return _request(url, method, headers=headers)

    def exchange_info(self, symbol: str):
        return self.public_get("/api/v3/exchangeInfo", {"symbol": symbol.upper()})

    def symbol_rules(self, symbol: str):
        info = self.exchange_info(symbol)
        s = info["symbols"][0]
        tick = 0.01
        step = 0.0001
        min_qty = 0.0001
        min_notional = 5.0
        for f in s.get("filters", []):
            t = f.get("filterType")
            if t == "PRICE_FILTER":
                tick = float(f.get("tickSize", tick))
            elif t == "LOT_SIZE":
                step = float(f.get("stepSize", step))
                min_qty = float(f.get("minQty", min_qty))
            elif t in ("MIN_NOTIONAL", "NOTIONAL"):
                v = f.get("minNotional") or f.get("notional")
                if v is not None:
                    min_notional = float(v)
        return {"tick_size": tick, "step_size": step, "min_qty": min_qty, "min_notional": min_notional}

    def place_order(self, symbol: str, side: str, qty: float, order_type: str = "MARKET", price: float | None = None):
        endpoint = "/api/v3/order/test" if self.test_mode else "/api/v3/order"
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": f"{qty:.8f}".rstrip("0").rstrip("."),
        }
        if order_type.upper() != "MARKET" and price is not None:
            params["timeInForce"] = "GTC"
            params["price"] = f"{price:.8f}".rstrip("0").rstrip(".")
        return self.signed_request("POST", endpoint, params)
