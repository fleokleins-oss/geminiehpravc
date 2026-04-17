from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass
class EngineConfig:
    mode: str = "paper"
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    depth_level: int = 20
    depth_speed: str = "100ms"
    time_unit: str | None = None
    budget_usd: float = 40.0
    cooldown_ms: int = 1500
    max_position_pct: float = 0.25
    gene_path: Path = Path("shared_genes/genes.json")
    output_dir: Path = Path("output")
    live_base_url: str = "https://api.binance.com"
    testnet_base_url: str = "https://testnet.binance.vision"
    market_ws_base_url: str = "wss://data-stream.binance.vision"
