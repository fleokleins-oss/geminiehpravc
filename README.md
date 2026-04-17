# Execution Engine v2

Real execution-oriented engine for Binance Spot market data.

It includes:
- optional `uvloop`
- optional `orjson`
- combined trade + depth stream consumer
- microstructure scoring
- slippage model
- paper / testnet / live order routing
- local event logging
- optional gene loading from the Darwin lab

## Binance primitives used
- Market data only WebSocket endpoint
- combined streams
- partial book depth / trade streams
- microsecond timeUnit support
- signed REST order creation / test order

## Install
```bash
python -m venv exec-env
source exec-env/bin/activate
pip install -r requirements.txt
```

## Start in paper mode
```bash
chmod +x *.sh
./run_paper.sh
```

## Testnet
```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
./run_testnet.sh
```

## Live
```bash
export BINANCE_API_KEY=...
export BINANCE_API_SECRET=...
./run_live.sh
```

## Notes
- Paper mode is the default and safe.
- Live mode requires API keys with TRADE permission.
- If you do not want market orders, keep `MODE=paper` or `MODE=testnet` and iterate first.
