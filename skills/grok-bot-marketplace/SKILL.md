---
name: grok-bot-marketplace
description: Browse, search, filter, and compare public Grok Bots on the x.ai Bot marketplace catalog. Use when the user wants official marketplace listings, categories, or grokbot:// install links from the snapshot. There is no public marketplace REST or install API — return addHref plus the marketplace URL. For viral shares on X/Twitter, use grok-bot-x-feed instead.
license: MIT
compatibility: Requires Python 3.10+. Network only for refresh or --details. Works offline against data/catalog.json. X_BEARER_TOKEN is not required for this skill.
metadata:
  author: dadoedo
  version: "0.3.0"
---

# Grok Bot marketplace catalog

Help the user browse the public [Grok Bot marketplace](https://x.ai/bot/marketplace). This skill is the **official catalog** snapshot (HTML scrape → `data/catalog.json`).

For **viral/shared templates on X**, switch to the `grok-bot-x-feed` skill (`x-search` / `x-viral` / `x-monitor`). Live search needs `X_BEARER_TOKEN`; `--demo` / missing token uses a fixture. Marketplace list/search/compare work without it.

## Hard rules

1. **No install API.** There is no public Bot marketplace REST API. Do not invent list/install endpoints. Do not POST, PUT, or guess URLs under `x.ai` to install a bot.
2. **Install is a deep link.** Each bot has `addHref` like `grokbot://app/v1/bot-template?id=…`. Return `addHref` and `marketplaceUrl`. Tell the user to open those in Grok Bot (or the marketplace page).
3. **Catalog source.** Live data is SSR HTML at `https://x.ai/bot/marketplace` (`#marketplace-catalog`). A checked-in snapshot lives at `data/catalog.json`. Prefer the snapshot; refresh only when asked or when the snapshot is missing/stale.
4. **Do not search X from this skill.** Use `grok-bot-x-feed` for that.
6. **Do not store X API secrets.** Marketplace commands never need `X_BEARER_TOKEN`. If you switch to the X feed, read tokens from env / `.env` only.

## Workflow

Work from the **plugin root** (the directory that contains `plugin.json`).

```bash
python3 scripts/catalog.py list --with-categories
python3 scripts/catalog.py list --category Engineering
python3 scripts/catalog.py search "seo brief"
python3 scripts/catalog.py search "outbound" --format text
python3 scripts/catalog.py categories
python3 scripts/catalog.py show researchy --format text
python3 scripts/catalog.py compare researchy tinkabot --details
python3 scripts/catalog.py refresh
```

Default `--format` is `json`. Put `--format text` **after** the subcommand.

If Python cannot run, read `data/catalog.json` and filter it yourself.

## Output contract

Every bot you present MUST include `name`, `creator`, `description`, `categories`, `installCount` (return `0` honestly), `marketplaceUrl`, `addHref`. Also include `id`, `handle`, and `feed: marketplace` when available.

> Install is not an API call. Open `addHref` in Grok Bot, or open `marketplaceUrl` in a browser.
