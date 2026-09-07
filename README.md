# Grok Bot Marketplace

Cursor **Open Plugin** so agents can discover [Grok Bots](https://x.ai/bot/marketplace) two ways, from one public feed:

1. **Marketplace catalog** (`feed: marketplace`) — official x.ai listings
2. **X viral** (`feed: x`) — posts that share marketplace / `grokbot://` links

The plugin **only reads** [`https://grokbots.store/feed.json`](https://grokbots.store/feed.json) (override `GROKBOTS_FEED_URL`). A bundled snapshot is the offline fallback. **Users do not need an X API key.**

Operators on **hetzner-prod** refresh the feed (`ops/refresh_feed.py`) and publish it to Cloudflare R2. See [`ops/README.md`](ops/README.md).

It is a thin discovery layer, not a store and **not an installer**.

## Honesty: install is a link, not an API

There is **no public Bot marketplace REST API**. This plugin never installs a bot and must not call a fake install endpoint.

Each catalog card includes:

```text
feed:         marketplace
addHref:      grokbot://app/v1/bot-template?id=…
marketplace:  https://x.ai/bot/marketplace/bots/{id}
```

Open `addHref` in Grok Bot, or open the marketplace URL in a browser.

`installCount` is returned when present. **Marketplace SSR currently ships `0` for every public bot** — that is honest, not “unused”.

## Quick start

```bash
git clone https://github.com/dadoedo/grok-bot-marketplace-plugin.git
cd grok-bot-marketplace-plugin

python3 scripts/catalog.py list --with-categories --format text
python3 scripts/catalog.py search "outbound" --category Sales --format text
python3 scripts/catalog.py compare researchy tinkabot
python3 scripts/catalog.py x-viral --format text
```

Default source is the hosted feed. Offline:

```bash
python3 scripts/catalog.py list --offline
python3 scripts/catalog.py x-viral --demo --format text
```

Python 3.10+. Stdlib only — no pip packages.

Landing (`site/`): brand **grokbots.store**. Preview: `python3 -m http.server 8080 --directory site`.

## Two feeds

| `feed` | Command | User needs |
| --- | --- | --- |
| `marketplace` | `list` `search` `compare` `show` `categories` | network to grokbots.store, or `--offline` snapshot |
| `x` | `x-search` `x-viral` / `x-trending` | same hosted feed (`xViral`) |

`--live` on `x-*` is an **operator/debug** X API call (`X_BEARER_TOKEN`). It is not required to use the plugin.

Agents: skill `grok-bot-marketplace` for the catalog, `grok-bot-x-feed` for viral cards.

## Hosted feed

```text
GET https://grokbots.store/feed.json
# or GROKBOTS_FEED_URL

{
  "marketplace": { "bots": [ /* catalog document */ ] },
  "xViral": { "results": [ /* posts with addHref/marketplaceUrl when extractable */ ] },
  "fetchedAt": "ISO-8601",
  "sources": { "marketplace": "…", "x": "…" }
}
```

Bundled fallback: [`data/feed.json`](data/feed.json) (plus [`data/catalog.json`](data/catalog.json)). Rebuild with:

```bash
python3 ops/refresh_feed.py --from-snapshot --demo-x --out data/feed.json
```

## CLI

```bash
python3 scripts/catalog.py list [--category NAME] [--limit N] [--sort name|installs] [--format json|text]
python3 scripts/catalog.py search QUERY [--category NAME] [--format json|text]
python3 scripts/catalog.py categories
python3 scripts/catalog.py show ID_OR_NAME...
python3 scripts/catalog.py compare ID_OR_NAME...
python3 scripts/catalog.py x-viral --format text
python3 scripts/catalog.py x-search "researchy"
```

`--format json` is the default. Put `--format text` **after** the subcommand.

`--feed-url URL` overrides the hosted feed. `--offline` skips it.

`--details` on `show`/`compare` still fetches an x.ai bot page when you explicitly ask.

## Install the plugin

### cursor.directory

1. After merge, submit this GitHub repo at [cursor.directory/plugins/new](https://cursor.directory/plugins/new).
2. Users find **Grok Bot Marketplace** on [cursor.directory](https://cursor.directory) and install it.

The repo must stay **public** for directory/marketplace listing.

### Local

```bash
ln -s "$(pwd)" ~/.cursor/plugins/local/grok-bot-marketplace
```

Reload Cursor (**Developer: Reload Window**) → **Customize**.

## Operators (hetzner-prod)

Refresh host: `stredan-cursor-agent@46.224.84.45` (`Host stredan-cursor-hetzner-prod`). Publish object `feed.json` to R2 bucket `grokbots-feed` (Cloudflare Stredan). Full crontab, env, and wrangler/S3 steps: [`ops/README.md`](ops/README.md).

## Layout

| Path | Why |
| --- | --- |
| [`plugin.json`](plugin.json) | Agent Plugins 1.0.0 |
| [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) | Cursor Plugin manifest |
| [`skills/grok-bot-marketplace/`](skills/grok-bot-marketplace/SKILL.md) | Catalog skill |
| [`skills/grok-bot-x-feed/`](skills/grok-bot-x-feed/SKILL.md) | X viral skill (hosted feed) |
| [`scripts/catalog.py`](scripts/catalog.py) | CLI |
| [`scripts/feed_client.py`](scripts/feed_client.py) | Hosted feed fetch + snapshot fallback |
| [`ops/refresh_feed.py`](ops/refresh_feed.py) | hetzner-prod merge job |
| [`data/feed.json`](data/feed.json) | Last-good bundled feed |
| [`data/catalog.json`](data/catalog.json) | Marketplace snapshot |
| [`site/`](site/) | GitHub Pages landing (grokbots.store) |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Hosted-feed tests mock HTTP. CI does not need `X_BEARER_TOKEN`.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `unrecognized arguments: --format` | Put `--format` after the subcommand |
| Empty or stale bots | Hosted feed down — `--offline` uses `data/feed.json`. Operators: run `ops/refresh_feed.py` |
| `X_BEARER_TOKEN is not set` on `--live` | Expected for users. Product path does not use `--live` |
| Marketplace HTML scrape failed on the server | Bot challenge / HTML shape change — keep last feed.json |
| `installCount` all zeros | Expected today; do not treat as unused |

## License

[MIT](LICENSE) — see [CHANGELOG.md](CHANGELOG.md).
