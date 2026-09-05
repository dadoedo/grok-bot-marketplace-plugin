---
name: grok-bot-x-feed
description: Discover Grok Bot templates shared on X/Twitter via official X API v2 recent search, or the offline demo fixture. Use when the user wants viral or recently posted marketplace/template/share links, grokbot:// mentions, or a since-checkpoint monitor. Live search uses X_BEARER_TOKEN from env/.env only — never commit secrets. Read/search only — never post, never call a marketplace install API. For the official x.ai catalog snapshot, use grok-bot-marketplace instead.
license: MIT
compatibility: Requires Python 3.10+. Live recent search needs X_BEARER_TOKEN (or TWITTER_BEARER_TOKEN / X_API_BEARER_TOKEN) and covers about the last 7 days. Offline --demo / X_DEMO=1 works with no token.
metadata:
  author: dadoedo
  version: "0.3.0"
---

# Grok Bot X discovery feed

Find **shared / viral Grok Bot templates on X**. This is a second discovery surface next to the official marketplace catalog. Results are labeled `feed: x`. Joined catalog cards on a post are labeled `feed: marketplace`.

## When to use

- "What's spreading on X about Grok Bots?"
- "Any viral marketplace shares this week?"
- Recurring "since last run" monitor for new template posts
- Offline demo of the X feed before credentials arrive

Use `grok-bot-marketplace` instead when they want the full official listing, categories, or compare.

## Auth

Need `X_BEARER_TOKEN` only for **live** search (Developer Console → App → Keys and tokens → Bearer Token). Aliases: `TWITTER_BEARER_TOKEN`, `X_API_BEARER_TOKEN`. Optional plugin-root `.env` (copy `.env.example`). Process env wins over `.env`. **Never log, print, or write the token.**

App-only Bearer is enough (`GET https://api.x.com/2/tweets/search/recent`). Do not request user OAuth unless the user asks for private-account access (this plugin does not).

This package does **not** use Cursor's X MCP / pay-per-use credits.

## Demo / missing credentials

- `--demo` or `X_DEMO=1` reads `data/demo/x-search-recent.json` (no network).
- If the token is unset and `--live` was not passed, **fall back to that fixture** (exit 0). Print the setup JSON on stderr (`demoFallback: true`) and still emit demo results on stdout.
- `--live` without a token exits 3 with setup JSON. **Do not crash the marketplace skill.** Catalog commands still work.
- Demo runs must not write `data/x-checkpoint.json`.

Do not invent live posts. Demo cards are fixtures.

## Hard rules

1. **Read/search only.** Do not post, like, follow, or DM.
2. **No marketplace install API.** If a post has `grokbot://` or `https://x.ai/bot/marketplace/bots/{id}`, return those links for the user to open.
3. **No secrets in git or logs.** Tokens live in env / `.env` only.
4. **Join when you can.** If a slug/template id matches `data/catalog.json`, attach the catalog card (`name`, `creator`, `addHref`, `marketplaceUrl`, `feed: marketplace`). Otherwise return a raw share card (`feed: x`).
5. Recent search is ~**7 days**. Say so if results look sparse.

Detect: marketplace bot URLs, the marketplace listing URL, `grokbot://app/v1/bot-template?id=…`, and recognizable public bot-template / share links.

## Workflow

Plugin root:

```bash
python3 scripts/catalog.py x-search --demo --format text
python3 scripts/catalog.py x-viral --demo
python3 scripts/catalog.py x-trending --format json
python3 scripts/catalog.py x-search --live --format text
python3 scripts/catalog.py x-search "researchy" --sort engagement --live
python3 scripts/catalog.py x-monitor --live
python3 scripts/x_feed.py viral --demo --max-results 25
```

- `x-search` — matching posts (default query covers `x.ai/bot/marketplace`, `grokbot://app/v1/bot-template`, and "Grok Bot" + marketplace/template/share). Extra keywords are ANDed unless the query already looks like an X search.
- `x-viral` / `x-trending` — same search ranked by engagement.
- `x-monitor` — posts newer than `data/x-checkpoint.json` (`since_id`). Writes the checkpoint on **live** success. `--reset` ignores it.
- `--format json` is default; put `--format text` after the subcommand.

## Output

Each result includes `feed: x`, post URL, author, text snippet, engagement metrics when present, extracted marketplace URLs / `addHref` / bot ids / share URLs, and `matchedBots` (catalog cards with `feed: marketplace`) or empty (raw share).

Envelope: `"feed": "x"`, `"demo": true|false`, `"live": true|false`.
