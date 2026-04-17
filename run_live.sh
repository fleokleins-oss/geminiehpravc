#!/usr/bin/env bash
set -euo pipefail
export MODE=live
export SYMBOLS="${SYMBOLS:-btcusdt,ethusdt}"
export DEPTH_LEVEL="${DEPTH_LEVEL:-20}"
export DEPTH_SPEED="${DEPTH_SPEED:-100ms}"
export BUDGET_USD="${BUDGET_USD:-40}"
python3 -m execution.cli
