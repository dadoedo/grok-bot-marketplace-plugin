# grokbots.store feed ops (hetzner-prod)

The **published plugin only reads** `https://grokbots.store/feed.json` (override `GROKBOTS_FEED_URL`), then the bundled `data/feed.json` snapshot. Users never set `X_BEARER_TOKEN`.

This directory is the **operator** job on **hetzner-prod cron**: scrape marketplace HTML + X recent search → merge `feed.json` → upload to R2. Cloudflare/Stredan = DNS + serve the file. **Do not** use a Worker as the scraper. **Do not** run this cron on the Grok Bot agent box.

## Host

```
Host stredan-cursor-hetzner-prod
    HostName 46.224.84.45
    User stredan-cursor-agent
    IdentityFile ~/.ssh/stredan-cursor-hetzner-prod
    IdentitiesOnly yes
```

Install path: `~/grokbots`.

Live layout (already synced): `ops/`, `scripts/`, `data/` on `stredan-cursor-agent@46.224.84.45` (`ubuntu-8gb-nbg1-1`). Crontab uses `SKIP_PUBLISH=1` until Cloudflare/R2 tokens exist. `~/grokbots/.env` is mode `600` from `ops/env.example` — **Bearer is empty**. Drop `X_BEARER_TOKEN` there (ops only) when the X App is on a Project.

## Refresh

```bash
cd ~/grokbots
# Operator env only — never commit. ~/grokbots/.env
#   X_BEARER_TOKEN=…
python3 ops/refresh_feed.py --out ~/grokbots/data/feed.json --catalog-out ~/grokbots/data/catalog.json
```

Exit codes: `0` ok · `2` marketplace scrape failed · `3` X Bearer missing · `4` X search failed (marketplace still written).

Until the X App is on a Project, recent search may 403 `client-not-enrolled`. Keep marketplace shipping:

```bash
python3 ops/refresh_feed.py --out ~/grokbots/data/feed.json --allow-x-failure
```

CI / offline snapshot (no live HTML, no live X):

```bash
python3 ops/refresh_feed.py --from-snapshot --demo-x --out data/feed.json
```

## Publish to R2

Stredan account `079006e0814dbf8ad1645014180e53f6`. DNS for grokbots.store is already on Cloudflare.

| | |
| --- | --- |
| Bucket | **`grokbots-feed`** (already exists) |
| Object key | `feed.json` |
| Public URL goal | `https://grokbots.store/feed.json` |

### wrangler

```bash
export CLOUDFLARE_ACCOUNT_ID=079006e0814dbf8ad1645014180e53f6
# CLOUDFLARE_API_TOKEN with R2 edit — server .env only
npx wrangler r2 object put grokbots-feed/feed.json --file=data/feed.json --remote
bash ops/publish_feed.sh data/feed.json
```

### S3-compatible API

Endpoint: `https://079006e0814dbf8ad1645014180e53f6.r2.cloudflarestorage.com`

```bash
aws s3 cp data/feed.json s3://grokbots-feed/feed.json \
  --endpoint-url https://079006e0814dbf8ad1645014180e53f6.r2.cloudflarestorage.com \
  --content-type application/json
```

Needs `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from an R2 API token. Never commit them.

### Public URL wiring (later — DNS already on Cloudflare)

Uploading the object does **not** by itself make `https://grokbots.store/feed.json` live. Do one of these after upload works:

1. **R2 custom domain** — R2 → `grokbots-feed` → Settings → Custom Domains → attach `grokbots.store` (or `feed.grokbots.store`) so `/feed.json` serves object `feed.json`.
2. **Worker (serve only)** — bind the bucket, `GET /feed.json` → `env.BUCKET.get("feed.json")` with `content-type: application/json`. Not a refresh job.
3. **Pages/static** — `PAGES_OUT=site/feed.json` then `wrangler pages deploy`, custom domain grokbots.store.

Until that is wired, the plugin uses the in-repo snapshot. Do **not** require R2 public access to ship the plugin.

## Cron (hetzner-prod only)

Copy `ops/env.example` → `~/grokbots/.env` (`chmod 600`).

**Installed today** (refresh only):

```cron
*/30 * * * * SKIP_PUBLISH=1 /home/stredan-cursor-agent/grokbots/ops/cron-refresh.sh
```

After Cloudflare/R2 tokens are in `.env`, drop `SKIP_PUBLISH`:

```cron
*/30 * * * * /home/stredan-cursor-agent/grokbots/ops/cron-refresh.sh
```

Same as `crontab ops/crontab.example`. Logs: `~/grokbots/ops/refresh.log`.

One-liner equivalent:

```cron
*/30 * * * * cd /home/stredan-cursor-agent/grokbots && set -a && . ./.env && set +a && /usr/bin/python3 ops/refresh_feed.py --out data/feed.json --allow-x-failure >> ops/refresh.log 2>&1 && /usr/bin/bash ops/publish_feed.sh data/feed.json >> ops/refresh.log 2>&1
```

## Env vars

| Name | Who | Required |
| --- | --- | --- |
| `X_BEARER_TOKEN` | hetzner-prod only | live X search |
| `GROKBOTS_FEED_URL` | plugin (optional) | default `https://grokbots.store/feed.json` |
| `GROKBOTS_OFFLINE=1` | plugin/CI | skip hosted fetch |
| `CLOUDFLARE_API_TOKEN` | hetzner-prod publish | wrangler R2 put |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | hetzner-prod publish | S3 API fallback |
| `CF_ACCOUNT_ID` | publish script | default Stredan `079006e0814dbf8ad1645014180e53f6` |
| `R2_BUCKET` / `R2_KEY` | publish script | default `grokbots-feed` / `feed.json` |
| `PAGES_OUT` | publish script | copy to a Pages/static path instead of R2 |
| `SKIP_PUBLISH=1` | cron-refresh.sh | refresh only, no upload |

Never commit `.env`, tokens, or SSH keys. Do not log Bearer values.
