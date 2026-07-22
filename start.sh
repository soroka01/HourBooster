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
  python3 -m venv .venv
fi

echo "[SETUP] Installing dependencies into .venv..."
.venv/bin/python -m pip install -r requirements.txt

exec .venv/bin/python HourBooster.py "$@"
