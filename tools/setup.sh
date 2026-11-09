#!/usr/bin/env bash
# Create venv and install the local tooling (dsw-tdk renders with the same engine as DSW 5).
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r tools/requirements.txt
echo
echo "Done. Activate with:  . .venv/bin/activate"
echo "Try:                  bash tools/check.sh path/to/context.json"
