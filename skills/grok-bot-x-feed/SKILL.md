---
name: grok-bot-x-feed
description: Discover Grok Bot templates shared on X/Twitter via official X API v2 recent search. Use when the user wants viral or recently posted marketplace/template/share links, grokbot:// mentions, or a since-checkpoint monitor. Requires X_BEARER_TOKEN. Read/search only — never post, never call a marketplace install API. For the official x.ai catalog snapshot, use grok-bot-marketplace instead.
license: MIT
compatibility: Requires Python 3.10+, network access, and X_BEARER_TOKEN (or TWITTER_BEARER_TOKEN / X_API_BEARER_TOKEN). Recent search covers about the last 7 days.
metadata:
  author: dadoedo
  version: "0.2.0"
---

# Grok Bot X discovery feed

Find **shared / viral Grok Bot templates on X** using the user's own X API app Bearer token. This is a second discovery surface next to the official marketplace catalog.

## When to use

- "What's spreading on X about Grok Bots?"
- "Any viral marketplace shares this week?"
- Recurring "since last run" monitor for new template posts

Use `grok-bot-marketplace` instead when they want the full official listing, categories, or compare.

## Auth

Need `X_BEARER_TOKEN` (Developer Console → App → Keys and tokens → Bearer Token). Aliases: `TWITTER_BEARER_TOKEN`, `X_API_BEARER_TOKEN`. Optional plugin-root `.env` (copy `.env.example`). Process env wins over `.env`.

If unset, the CLI exits 3 with a setup JSON payload. **Do not crash the marketplace skill.** Tell the user how to set the token; catalog commands still work.

This package does **not** use Cursor's X MCP / pay-per-use credits.

## Hard rules

1. **Read/search only.** Do not post, like, follow, or DM.
2. **No marketplace install API.** If a post has `grokbot://` or `https://x.ai/bot/marketplace/bots/{id}`, return those links for the user to open.
3. **Join when you can.** If a slug/template id matches `data/catalog.json`, attach the catalog card (`name`, `creator`, `addHref`, `marketplaceUrl`). Otherwise return a raw share card.
4. Recent search is ~**7 days**. Say so if results look sparse.

## Workflow

Plugin root:

```bash
python3 scripts/catalog.py x-search --format text
python3 scripts/catalog.py x-search "researchy" --sort engagement
python3 scripts/catalog.py x-monitor
python3 scripts/x_feed.py search --max-results 25
```

- `x-search` — latest matching posts (default query covers `x.ai/bot/marketplace`, `grokbot://app/v1/bot-template`, and "Grok Bot" + marketplace/template/share). Extra keywords are ANDed unless the query already looks like an X search.
- `x-monitor` — posts newer than `data/x-checkpoint.json` (`since_id`). Writes the checkpoint on success. `--reset` ignores it. Suitable for a later recurring routine.
- `--format json` is default; put `--format text` after the subcommand.

## Output

Each result includes post URL, author, text snippet, engagement metrics when present, extracted marketplace URLs / `addHref` / bot ids, and `matchedBots` (catalog cards) or empty (raw share).

If `X_BEARER_TOKEN` is missing, show the setup hint from the CLI stderr JSON. Do not invent posts.
