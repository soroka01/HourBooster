#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "config/config.ini" ]]; then
  echo "[ERROR] config/config.ini was not found."
  echo "Copy config/config.ini.example to config/config.ini and configure Telegram access."
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[SETUP] Creating local .venv..."
  python3.14 -m venv .venv
fi

if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)'; then
  echo "[ERROR] .venv uses Python older than 3.14. Recreate it with Python 3.14 or newer."
  exit 1
fi

echo "[SETUP] Updating pip, setuptools and wheel in .venv..."
.venv/bin/python -m pip install --quiet --upgrade 'pip==26.1.2' 'setuptools==84.0.0' 'wheel==0.48.0'

echo "[SETUP] Installing dependencies into .venv..."
.venv/bin/python -m pip install -r requirements.txt

exec .venv/bin/python HourBooster.py "$@"
