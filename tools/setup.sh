#!/usr/bin/env bash
# Create venv and install minimal deps for local DSW template rendering.
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
echo "Try:                  python tools/render.py --list-chapters"
echo "                      python tools/render.py --dump-replies -o replies.json"
echo "                      python tools/render.py -o out.json"
