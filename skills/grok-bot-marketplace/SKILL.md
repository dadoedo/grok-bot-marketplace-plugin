---
name: grok-bot-marketplace
description: Browse, search, filter, and compare public Grok Bots on the x.ai Bot marketplace. Use when the user wants to find a Grok Bot template, look up a creator, filter by category, compare bots, or get a grokbot:// install link. There is no public marketplace REST or install API — return addHref plus the marketplace URL for the user to open.
license: MIT
compatibility: Requires Python 3.10+ and network access only when refreshing the catalog or fetching bot detail pages. Works offline against data/catalog.json.
metadata:
  author: dadoedo
  version: "0.1.0"
---

# Grok Bot marketplace

Help the user browse the public [Grok Bot marketplace](https://x.ai/bot/marketplace). This plugin is a thin catalog viewer.

## Hard rules

1. **No install API.** There is no public Bot marketplace REST API. Do not invent list/install endpoints. Do not POST, PUT, or guess URLs under `x.ai` to install a bot.
2. **Install is a deep link.** Each bot has `addHref` like `grokbot://app/v1/bot-template?id=…`. Return `addHref` and `marketplaceUrl`. Tell the user to open those in Grok Bot (or the marketplace page).
3. **Catalog source.** Live data is SSR HTML at `https://x.ai/bot/marketplace` (`#marketplace-catalog`). A checked-in snapshot lives at `data/catalog.json`. Prefer the snapshot; refresh only when asked or when the snapshot is missing/stale.
4. **Do not block on X / Twitter.** This skill does not search X.

## When to use

- "What Grok Bots exist?" / "list marketplace bots"
- "Find a bot for SEO / recruiting / design"
- "Who made Researchy?" / "compare these bots"
- "How do I add/install this Grok Bot?"

## Workflow

Work from the **plugin root** (the directory that contains `plugin.json`).

### 1. List or search (default)

```bash
python3 scripts/catalog.py list --with-categories
python3 scripts/catalog.py list --category Engineering
python3 scripts/catalog.py search "seo brief"
python3 scripts/catalog.py categories
python3 scripts/catalog.py show researchy
```

If you cannot run Python, read `data/catalog.json` and filter it yourself.

### 2. Compare a few bots

```bash
python3 scripts/catalog.py compare researchy seo-aeo-desk tinkabot
```

Add `--details` only when catalog descriptions are not enough. That fetches each `https://x.ai/bot/marketplace/bots/{id}` page and attaches instructions (when present), memories, skills, routines, and integrations. Keep `--details` to 2–4 bots.

### 3. Refresh the snapshot (optional)

```bash
python3 scripts/catalog.py refresh
# or
python3 scripts/refresh-catalog.py
```

Refresh fetches the live marketplace HTML, parses the embedded `templates` array, and rewrites `data/catalog.json`. If fetch/parse fails, keep the snapshot and report the error. Do not fabricate bots.

## Output contract

Every bot you present MUST include:

| Field | Source |
| --- | --- |
| `name` | catalog `name` |
| `creator` | catalog `creatorName` |
| `description` | `summary` or `description` |
| `categories` | catalog `categories` |
| `installCount` | include when present (may be `0` or unknown) |
| `marketplaceUrl` | `https://x.ai/bot/marketplace/bots/{id}` |
| `addHref` | `grokbot://…` install deep link |

Also include `id` and `handle` when available. After the list, remind the user:

> Install is not an API call. Open `addHref` in Grok Bot, or open `marketplaceUrl` in a browser.

## How the catalog is parsed

The marketplace page embeds the full public catalog (~69 bots) in the Next.js `self.__next_f` payload as `templates[]`. Fields typically include `id`, `name`, `creatorName`, `handle`, `description` / `summary`, `categories`, `color`, `shape`, `imageUrl`, `installCount`, `addHref`. Creator images are hosted on `grok-bot-marketplace-public-assets.s3.amazonaws.com` (informational only).

Detail pages use the same bot object and may fill `instructions`, `memories`, `skills`, `routines`, and `integrations`. Listing HTML often leaves `instructions` empty — use `--details` for compare.

## What not to do

- Do not call `xai-org/plugin-marketplace` or any Grok **Build** plugin registry. That is a different catalog.
- Do not scrape X for viral bots (out of scope for this MVP).
- Do not dump full skill `content` blobs unless the user asked for a deep compare.

## Example

User: "Find a Grok Bot for outbound sales."

1. Run `python3 scripts/catalog.py search "outbound" --category Sales` (or search without category if unsure).
2. Show matching cards with creator, description, categories, installCount, marketplace URL, addHref.
3. Offer to compare the top 2–3 with `--details` if they want a closer look.
