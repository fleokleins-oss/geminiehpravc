from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass

try:
    import uvloop  # type: ignore
    def install_uvloop_if_available():
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except Exception:
    def install_uvloop_if_available():
        return

try:
    import orjson  # type: ignore
    def loads(raw):
        return orjson.loads(raw if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8"))
except Exception:
    def loads(raw):
        return json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)

import websockets

@dataclass
class WSUpdate:
    stream: str
    data: dict

def build_stream_names(symbols, depth_level=20, depth_speed="100ms"):
    out = []
    for s in symbols:
        s = s.lower()
        out.append(f"{s}@trade")
        out.append(f"{s}@depth{depth_level}@{depth_speed}")
    return out

async def stream_updates(symbols, base_url, depth_level=20, depth_speed="100ms", time_unit=None):
    streams = build_stream_names(symbols, depth_level, depth_speed)
    url = f"{base_url}/stream?streams={'/'.join(streams)}"
    if time_unit:
        url += f"&timeUnit={time_unit}"
    async with websockets.connect(url, ping_interval=20, ping_timeout=60, close_timeout=10, max_queue=1024) as ws:
        while True:
            raw = await ws.recv()
            payload = loads(raw)
            if isinstance(payload, dict) and "stream" in payload and "data" in payload:
                yield WSUpdate(stream=payload["stream"], data=payload["data"])
            elif isinstance(payload, dict):
                yield WSUpdate(stream="", data=payload)
