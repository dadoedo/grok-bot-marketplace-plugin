# grok-bot-marketplace-plugin

Thin [Cursor](https://cursor.com) community **Open Plugin** so agents can browse and search the public [Grok Bot marketplace](https://x.ai/bot/marketplace).

Weekend-sized MVP: visibility into the catalog before Cursor ships an official browse surface. It is not a deep product.

## What it does

- Lists public Grok Bots from the marketplace catalog
- Searches / filters by keyword or category
- Compares a few bots
- Always returns **name**, **creator**, **description**, **categories**, **installCount** (when present), **marketplace URL**, and **addHref**. Marketplace SSR currently ships `installCount: 0` for every public bot — returning `0` is honest; do not treat it as "unused" or rank by popularity until non-zero values appear.

## Honesty: install is not an API

There is **no public Bot marketplace REST API**. This plugin does not install bots and must not call a fake install endpoint.

Install is only a deep link on each card:

```text
grokbot://app/v1/bot-template?id=…
```

Skills and the CLI return that `addHref` plus `https://x.ai/bot/marketplace/bots/{id}` so **you** can open them in Grok Bot or a browser.

## Catalog source

The marketplace page at [https://x.ai/bot/marketplace](https://x.ai/bot/marketplace) (`#marketplace-catalog`) is SSR HTML. The full public catalog is embedded in the page payload (`templates[]`: `id`, `name`, `creatorName`, `handle`, `description` / `summary`, `categories`, `color`, `shape`, `imageUrl`, `installCount`, `addHref`).

**`installCount` is currently non-signal.** The live page embeds `installCount: 0` for all bots. The CLI still returns that field. Do not infer popularity, unused-ness, or sort quality from zeros until the marketplace starts shipping non-zero counts.

A checked-in snapshot lives at [`data/catalog.json`](data/catalog.json). Agents should use it by default. Re-fetch when you want a live refresh:

```bash
python3 scripts/catalog.py refresh
# same thing:
python3 scripts/refresh-catalog.py
```

Detail pages (`https://x.ai/bot/marketplace/bots/{id}`) are fetched only for `--details` compare/show.

Creator images are hosted on `grok-bot-marketplace-public-assets.s3.amazonaws.com` (informational only).

## Layout

This repo is a **single plugin** at the repository root (not a multi-plugin marketplace repo).

| Path | Why |
| --- | --- |
| [`plugin.json`](plugin.json) | [Agent Plugins](https://agent-plugins.org) 1.0.0 manifest (portable Open Plugin) |
| [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) | Cursor Plugin manifest ([cursor.directory](https://cursor.directory) / later Cursor Marketplace) |
| [`skills/grok-bot-marketplace/SKILL.md`](skills/grok-bot-marketplace/SKILL.md) | Agent skill: list / search / compare |
| [`scripts/catalog.py`](scripts/catalog.py) | Snapshot loader, search, compare, HTML refresh (Python 3 stdlib only) |
| [`data/catalog.json`](data/catalog.json) | Checked-in catalog snapshot |

[cursor.directory](https://cursor.directory) auto-detects `skills/*/SKILL.md`. Cursor also loads Agent Plugins from root `plugin.json` and Cursor Plugins from `.cursor-plugin/plugin.json`.

## Install

### cursor.directory (community — intended publish path)

1. Publisher: submit this GitHub repo at [cursor.directory/plugins/new](https://cursor.directory/plugins/new) (sign in, paste the repo URL, submit). No PR to `cursor/community-plugins` is required.
2. Users: find **Grok Bot Marketplace** on [cursor.directory](https://cursor.directory) and install from there.

### Local (dev)

```bash
git clone https://github.com/dadoedo/grok-bot-marketplace-plugin.git
ln -s "$(pwd)/grok-bot-marketplace-plugin" ~/.cursor/plugins/local/grok-bot-marketplace
```

Reload Cursor (**Developer: Reload Window**), then confirm the skill under **Customize**. On Teams/Enterprise, local plugin imports may need to be allowed.

Requires Python 3.10+ on the machine that runs `scripts/catalog.py`. No npm/pip dependencies.

### Optional later: curated Cursor Marketplace

After the community listing is up, you can also submit the same repo at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish). That is a separate, slower, manually reviewed queue — not required for this MVP.

## How agents should use the skill

When the user asks to browse Grok Bots, follow [`skills/grok-bot-marketplace/SKILL.md`](skills/grok-bot-marketplace/SKILL.md). From the plugin root:

```bash
python3 scripts/catalog.py list --with-categories
python3 scripts/catalog.py search "outbound" --category Sales
python3 scripts/catalog.py compare researchy tinkabot --details
python3 scripts/catalog.py show dr-eggbot-v2 --format text
python3 scripts/catalog.py search "outbound" --format text
```

`--format json` is the default (agent-friendly). Put `--format text` after the subcommand for a readable dump (`--format` also works before the subcommand).

If Python cannot run, read `data/catalog.json` and filter in-context. Still return `addHref` + `marketplaceUrl`. Never invent an install API.

## CLI

```bash
python3 scripts/catalog.py list [--category NAME] [--limit N] [--sort name|installs] [--format json|text]
python3 scripts/catalog.py search QUERY [--category NAME] [--format json|text]
python3 scripts/catalog.py categories [--format json|text]
python3 scripts/catalog.py show ID_OR_NAME... [--details] [--format json|text]
python3 scripts/catalog.py compare ID_OR_NAME... [--details] [--format json|text]
python3 scripts/catalog.py refresh [--format json|text]
```

```bash
python3 -m unittest discover -s tests -v
```

## Phase 2 (not in this MVP)

TODO: optional second feed of viral Grok Bot templates from X / Twitter. Do not block browse/search on X.

## License

[MIT](LICENSE)
