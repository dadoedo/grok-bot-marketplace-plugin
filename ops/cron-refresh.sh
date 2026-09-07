#!/usr/bin/env bash
# hetzner-prod wrapper: refresh feed then upload to R2.
# Intended for crontab. Does not print secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

mkdir -p "$ROOT/ops"
LOG="${REFRESH_LOG:-$ROOT/ops/refresh.log}"

{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) refresh ==="
  python3 "$ROOT/ops/refresh_feed.py" --out "$ROOT/data/feed.json" --catalog-out "$ROOT/data/catalog.json" --allow-x-failure
  if [[ "${SKIP_PUBLISH:-}" == "1" ]]; then
    echo "SKIP_PUBLISH=1 — not uploading"
  else
    bash "$ROOT/ops/publish_feed.sh" "$ROOT/data/feed.json" || echo "publish skipped/failed (see ops/README.md)"
  fi
} >>"$LOG" 2>&1
