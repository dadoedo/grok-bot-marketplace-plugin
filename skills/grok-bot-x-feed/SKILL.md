---
name: grok-bot-x-feed
description: Discover Grok Bot templates shared on X from the hosted grokbots.store feed (xViral). Use when the user wants viral or recently posted marketplace/template/share links or grokbot:// mentions. The published plugin does not call X and does not need X_BEARER_TOKEN. Read-only — never post, never call a marketplace install API. For the official catalog, use grok-bot-marketplace.
license: MIT
compatibility: Requires Python 3.10+. Default source is https://grokbots.store/feed.json. Offline --demo / bundled snapshot work with no token.
metadata:
  author: dadoedo
  version: "0.4.0"
---

# Grok Bot X discovery feed

Find **shared / viral Grok Bot templates** from the public feed’s `xViral` section. Results are labeled `feed: x`. Joined catalog cards are labeled `feed: marketplace`.

## When to use

- "What's spreading on X about Grok Bots?"
- "Any viral marketplace shares this week?"
- Offline demo of the X cards (`--demo`)

Use `grok-bot-marketplace` when they want the full official listing, categories, or compare.

## Auth

**End users: none.** Do not send people to developer.x.com. The plugin fetches `https://grokbots.store/feed.json` (or `GROKBOTS_FEED_URL`).

`--live` talks to X API v2 and needs `X_BEARER_TOKEN` — that is an **operator/debug** path (hetzner-prod uses `ops/refresh_feed.py`). Never log or write the token.

This package does **not** use Cursor's X MCP / pay-per-use credits.

## Demo / offline

- Default: hosted feed `xViral`, then bundled `data/feed.json`.
- `--demo` or `X_DEMO=1` reads `data/demo/x-search-recent.json` (no network).
- `--offline` skips grokbots.store.
- Do not invent live posts.

## Hard rules

1. **Read/search only.** Do not post, like, follow, or DM.
2. **No marketplace install API.** If a post has `grokbot://` or `https://x.ai/bot/marketplace/bots/{id}`, return those links for the user to open.
3. **Join when you can.** Attach catalog cards (`name`, `creator`, `addHref`, `marketplaceUrl`, `feed: marketplace`) when a slug/template id matches. Otherwise return a raw share card (`feed: x`).

Detect: marketplace bot URLs, the marketplace listing URL, `grokbot://app/v1/bot-template?id=…`, and recognizable public bot-template / share links.

## Workflow

Plugin root:

```bash
python3 scripts/catalog.py x-viral --format text
python3 scripts/catalog.py x-search --format json
python3 scripts/catalog.py x-search "researchy"
python3 scripts/catalog.py x-viral --demo
python3 scripts/catalog.py x-search --offline
```

- `x-search` / `x-viral` / `x-trending` read hosted `xViral` (engagement sort for viral).
- `--format json` is default; put `--format text` after the subcommand.

## Output

Each result includes `feed: x`, post URL, author, text snippet, engagement metrics when present, extracted marketplace URLs / `addHref` / bot ids, and `matchedBots` (catalog cards with `feed: marketplace`) or empty (raw share).

Envelope: `"feed": "x"`, `"live": false` on the product path.
