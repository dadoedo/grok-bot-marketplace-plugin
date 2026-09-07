# grokbots.store feed ops (hetzner-prod)

The **published Cursor plugin only reads** `https://grokbots.store/feed.json`.
This directory is the **operator** job: scrape + merge + publish. Users never set
`X_BEARER_TOKEN`.

## Host

SSH alias (do not use the Grok Bot agent box as the cron host):

```
Host stredan-cursor-hetzner-prod
    HostName 46.224.84.45
    User stredan-cursor-agent
```

Suggested install path on the box: `~/grokbots` (clone or rsync this repo).

## Refresh

```bash
cd ~/grokbots
# Operator env only — never commit. Drop in ~/grokbots/.env
#   X_BEARER_TOKEN=…
python3 ops/refresh_feed.py --out ~/grokbots/data/feed.json --catalog-out ~/grokbots/data/catalog.json
```

Exit codes: `0` ok · `2` marketplace scrape failed · `3` X Bearer missing · `4` X search failed (marketplace still written).

Until the X App is enrolled on a Project, recent search may 403 `client-not-enrolled`. Keep running marketplace refresh:

```bash
python3 ops/refresh_feed.py --out ~/grokbots/data/feed.json --allow-x-failure
```

Offline / CI snapshot (no live X, no live HTML):

```bash
python3 ops/refresh_feed.py --from-snapshot --demo-x --out data/feed.json
```

## Publish

Stredan Cloudflare account `079006e0814dbf8ad1645014180e53f6`. DNS for grokbots.store is already on Cloudflare. **Refresh runs on hetzner-prod cron** — do not use a Worker as the primary scraper.

Public URL goal: `https://grokbots.store/feed.json`.

### R2 (preferred once public access is wired)

Bucket **`grokbots-feed`** (already created). Object key: `feed.json`.

Custom domain / Worker in front of the object is a later DNS step. Until that exists, upload still lands in R2; the plugin falls back to `data/feed.json`.

#### wrangler

```bash
export CLOUDFLARE_ACCOUNT_ID=079006e0814dbf8ad1645014180e53f6
# CLOUDFLARE_API_TOKEN with R2 edit — on the server env file, not git
npx wrangler r2 object put grokbots-feed/feed.json --file=data/feed.json --remote
# or:
bash ops/publish_feed.sh data/feed.json
```

#### S3-compatible API

R2 S3 endpoint: `https://079006e0814dbf8ad1645014180e53f6.r2.cloudflarestorage.com`

```bash
aws s3 cp data/feed.json s3://grokbots-feed/feed.json \
  --endpoint-url https://079006e0814dbf8ad1645014180e53f6.r2.cloudflarestorage.com \
  --content-type application/json
```

Requires an R2 API token (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`). Never commit them.

### Cloudflare Pages / static file (no R2 public URL yet)

If you want `https://grokbots.store/feed.json` before R2 custom-domain is attached:

1. Copy `data/feed.json` into a Pages project (or this repo’s `site/feed.json`).
2. Deploy Pages with grokbots.store as the custom domain.
3. Or `npx wrangler pages deploy site --project-name grokbots-store`.

Do **not** require R2 public access to ship the plugin — the snapshot fallback is in-repo.

## Cron (hetzner-prod)

Do **not** use the Grok Bot agent box as the cron host.

Install path: `~/grokbots`. Copy `ops/env.example` → `~/grokbots/.env` (`chmod 600`). Put `X_BEARER_TOKEN` there when the X App is on a Project; until then `--allow-x-failure` still refreshes marketplace.

```cron
# crontab ops/crontab.example
*/30 * * * * /home/stredan-cursor-agent/grokbots/ops/cron-refresh.sh
```

Equivalent one-liner (logs to `~/grokbots/ops/refresh.log`):

```cron
*/30 * * * * cd /home/stredan-cursor-agent/grokbots && set -a && . ./.env && set +a && /usr/bin/python3 ops/refresh_feed.py --out data/feed.json --allow-x-failure >> ops/refresh.log 2>&1 && /usr/bin/bash ops/publish_feed.sh data/feed.json >> ops/refresh.log 2>&1
```

`--allow-x-failure` keeps marketplace updates shipping while X enrollment is pending (`client-not-enrolled` 403).

## Env vars

| Name | Who | Required |
| --- | --- | --- |
| `X_BEARER_TOKEN` | hetzner-prod only | live X search |
| `GROKBOTS_FEED_URL` | plugin (optional) | default `https://grokbots.store/feed.json` |
| `GROKBOTS_OFFLINE=1` | plugin/CI | skip hosted fetch |
| `CLOUDFLARE_API_TOKEN` | hetzner-prod publish | wrangler R2 put |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | hetzner-prod publish | S3 API fallback |
| `CF_ACCOUNT_ID` | publish script | default Stredan id |
| `R2_BUCKET` / `R2_KEY` | publish script | default `grokbots-feed` / `feed.json` |
| `PAGES_OUT` | publish script | copy to a Pages/static path instead of R2 |
| `SKIP_PUBLISH=1` | cron-refresh.sh | refresh only, no upload |

## Secrets

Never commit `.env`, tokens, or SSH keys. Do not log Bearer values.
