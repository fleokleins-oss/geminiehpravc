from __future__ import annotations
import argparse
import asyncio
import os
from .config import EngineConfig
from .engine import ExecutionEngine

def parse_args():
    p = argparse.ArgumentParser(description="APEX exchange-oriented execution engine")
    p.add_argument("--mode", choices=["paper", "testnet", "live"], default=os.environ.get("MODE", "paper"))
    p.add_argument("--symbols", default=os.environ.get("SYMBOLS", "BTCUSDT,ETHUSDT"))
    p.add_argument("--depth-level", type=int, default=int(os.environ.get("DEPTH_LEVEL", "20")))
    p.add_argument("--depth-speed", default=os.environ.get("DEPTH_SPEED", "100ms"))
    p.add_argument("--time-unit", default=os.environ.get("TIME_UNIT", None))
    p.add_argument("--budget-usd", type=float, default=float(os.environ.get("BUDGET_USD", "40")))
    p.add_argument("--cooldown-ms", type=int, default=int(os.environ.get("COOLDOWN_MS", "1500")))
    p.add_argument("--duration-min", type=float, default=float(os.environ.get("DURATION_MIN", "0")))
    return p.parse_args()

async def main_async():
    a = parse_args()
    cfg = EngineConfig(
        mode=a.mode,
        symbols=[s.strip().upper() for s in a.symbols.split(",") if s.strip()],
        depth_level=a.depth_level,
        depth_speed=a.depth_speed,
        time_unit=a.time_unit,
        budget_usd=a.budget_usd,
        cooldown_ms=a.cooldown_ms,
    )
    engine = ExecutionEngine(cfg)
    await engine.run(duration_min=a.duration_min)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
