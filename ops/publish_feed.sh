#!/usr/bin/env bash
# Upload feed.json to Cloudflare R2 bucket grokbots-feed (Stredan).
# Operator script for hetzner-prod. Does not print secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="${1:-$ROOT/data/feed.json}"
BUCKET="${R2_BUCKET:-grokbots-feed}"
KEY="${R2_KEY:-feed.json}"
ACCOUNT_ID="${CF_ACCOUNT_ID:-079006e0814dbf8ad1645014180e53f6}"

if [[ ! -f "$FILE" ]]; then
  echo "missing feed file: $FILE" >&2
  exit 2
fi

if command -v wrangler >/dev/null 2>&1; then
  wrangler r2 object put "${BUCKET}/${KEY}" --file="$FILE" --remote --account-id="$ACCOUNT_ID"
  echo "uploaded ${BUCKET}/${KEY} via wrangler"
  exit 0
fi

if [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]] && command -v aws >/dev/null 2>&1; then
  ENDPOINT="${R2_ENDPOINT:-https://${ACCOUNT_ID}.r2.cloudflarestorage.com}"
  aws s3 cp "$FILE" "s3://${BUCKET}/${KEY}" --endpoint-url "$ENDPOINT" --content-type application/json
  echo "uploaded s3://${BUCKET}/${KEY} via aws cli"
  exit 0
fi

if [[ -n "${PAGES_OUT:-}" ]]; then
  mkdir -p "$(dirname "$PAGES_OUT")"
  cp "$FILE" "$PAGES_OUT"
  echo "copied feed to $PAGES_OUT (Pages/static path)"
  exit 0
fi

echo "No upload tool. Install wrangler, or set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY for the R2 S3 API." >&2
echo "Or set PAGES_OUT=/path/to/site/feed.json for a static/Pages copy. See ops/README.md" >&2
exit 3
