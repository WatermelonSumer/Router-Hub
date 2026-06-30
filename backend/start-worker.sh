#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v poetry >/dev/null 2>&1; then
  echo "poetry not found in PATH" >&2
  exit 1
fi

cd "${ROOT_DIR}"
exec poetry run python -m app.worker.scheduler
