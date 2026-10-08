#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/uvicorn ]]; then
  exec .venv/bin/uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" "$@"
fi
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" "$@"
