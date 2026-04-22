#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/smoke.py --only ollama "$@"
