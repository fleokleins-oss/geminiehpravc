#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d exec-env ]]; then
  python -m venv exec-env
fi

source exec-env/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

chmod +x run_paper.sh run_testnet.sh run_live.sh

echo "Ready."
echo "Paper:   ./run_paper.sh"
echo "Testnet: ./run_testnet.sh"
echo "Live:    ./run_live.sh"
