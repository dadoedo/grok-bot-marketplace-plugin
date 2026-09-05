# Grok Bot Marketplace

Cursor **Open Plugin** so agents can discover [Grok Bots](https://x.ai/bot/marketplace) two ways:

1. **Marketplace catalog** — the public listing on x.ai (offline snapshot + optional live HTML refresh)
2. **X discovery feed** — recent posts that share marketplace / `grokbot://` template links (official X API v2)

It is a thin discovery layer, not a store and **not an installer**.

## Honesty: install is a link, not an API

There is **no public Bot marketplace REST API**. This plugin never installs a bot and must not call a fake install endpoint.

Each catalog card includes:

```text
addHref:      grokbot://app/v1/bot-template?id=…
marketplace:  https://x.ai/bot/marketplace/bots/{id}
```

Open `addHref` in Grok Bot, or open the marketplace URL in a browser.

`installCount` is returned when present. **Marketplace SSR currently ships `0` for every public bot** — that is honest, not “unused”. Do not rank by popularity until non-zero values appear.

## Quick start

```bash
git clone https://github.com/dadoedo/grok-bot-marketplace-plugin.git
cd grok-bot-marketplace-plugin

python3 scripts/catalog.py list --with-categories --format text
python3 scripts/catalog.py search "outbound" --category Sales --format text
python3 scripts/catalog.py compare researchy tinkabot
```

Example (truncated):

```text
- Outbound Prospecting — Krista Letz @kristaletz
  Finds prospects that match your ideal customer, then drafts a first message…
  categories: From Grok Bot Team, Sales  installs: 0  id: pg
  marketplace: https://x.ai/bot/marketplace/bots/pg
  addHref: grokbot://app/v1/bot-template?id=i03IaF768-ielyzegoGye
```

Python 3.10+. Stdlib only — no pip packages.

## Two feeds

| Feed | Command | Needs network | Needs `X_BEARER_TOKEN` |
| --- | --- | --- | --- |
| Official catalog | `list` `search` `compare` `show` `categories` | only `refresh` / `--details` | no |
| Shares on X | `x-search` `x-monitor` | yes | yes |

Agents: use skill `grok-bot-marketplace` for the catalog, `grok-bot-x-feed` for X.

## Marketplace catalog

Source: SSR HTML at [https://x.ai/bot/marketplace](https://x.ai/bot/marketplace) (`#marketplace-catalog`). The full public list (~69 bots) is embedded in the Next.js `self.__next_f` payload (`templates[]`).

Checked-in snapshot: [`data/catalog.json`](data/catalog.json). Refresh:

```bash
python3 scripts/catalog.py refresh
python3 scripts/refresh-catalog.py
```

```bash
python3 scripts/catalog.py list [--category NAME] [--limit N] [--sort name|installs] [--format json|text]
python3 scripts/catalog.py search QUERY [--category NAME] [--format json|text]
python3 scripts/catalog.py categories
python3 scripts/catalog.py show ID_OR_NAME... [--details] [--format json|text]
python3 scripts/catalog.py compare ID_OR_NAME... [--details] [--format json|text]
python3 scripts/catalog.py refresh [--format json|text]
```

`--format json` is the default. Put `--format text` **after** the subcommand (it also works before). Category filter prefers an exact match, then substring.

`--details` fetches `https://x.ai/bot/marketplace/bots/{id}` for instructions/memories/skills when you are comparing a few bots.

Creator images live on `grok-bot-marketplace-public-assets.s3.amazonaws.com` (informational only).

## X discovery feed

Uses **your** X API v2 app-only Bearer token (`GET /2/tweets/search/recent`). Read/search only — this plugin never posts. It does **not** use Cursor’s X MCP or pay-per-use credits.

### Credentials

1. Create an App at [developer.x.com](https://developer.x.com) with **recent search / search Posts** access (typically X API Basic or higher).
2. Copy the **Bearer Token** (Keys and tokens).
3. Set it in the environment (do not commit it):

```bash
export X_BEARER_TOKEN='YOUR_TOKEN'
# or
cp .env.example .env   # then paste the token into .env
```

Accepted names (first non-empty wins):

| Variable | Role |
| --- | --- |
| `X_BEARER_TOKEN` | recommended |
| `TWITTER_BEARER_TOKEN` | alias |
| `X_API_BEARER_TOKEN` | alias |

A plugin-root `.env` is loaded with the stdlib (no python-dotenv). **Existing process env wins.** `.env` is gitignored.

If the token is missing, `x-search` / `x-monitor` exit `3` with a JSON setup payload. Marketplace commands still work.

### Search and monitor

```bash
python3 scripts/catalog.py x-search --format text
python3 scripts/catalog.py x-search "researchy" --sort engagement
python3 scripts/catalog.py x-monitor
python3 scripts/x_feed.py search --max-results 50
```

Default query matches:

- `x.ai/bot/marketplace`
- `grokbot://app/v1/bot-template`
- `"Grok Bot"` + marketplace / template / share

Extra keywords are ANDed with that filter unless the query already looks like an X search (`x.ai`, `grokbot`, `url:`).

Each hit includes post URL, author, text, public metrics, extracted marketplace / `grokbot://` links, and **joined catalog cards** when a bot slug or template id matches the snapshot. Unknown shares stay raw cards (still with whatever links were in the post).

`x-monitor` stores the newest tweet id in `data/x-checkpoint.json` and passes it as `since_id` next time. `--reset` ignores the checkpoint. Recent search only covers about **seven days**.

## Install the plugin

### cursor.directory (community — publish path)

1. After merge, submit this GitHub repo at [cursor.directory/plugins/new](https://cursor.directory/plugins/new).
2. Users find **Grok Bot Marketplace** on [cursor.directory](https://cursor.directory) and install it.

The repo is a single plugin at the root: Agent Plugins `plugin.json` plus Cursor `.cursor-plugin/plugin.json`, skills under `skills/*/SKILL.md`.

### Local

```bash
ln -s "$(pwd)" ~/.cursor/plugins/local/grok-bot-marketplace
```

Reload Cursor (**Developer: Reload Window**) → **Customize**. Teams/Enterprise may need local plugin imports allowed.

### Optional later: curated Cursor Marketplace

Same repo can go to [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) (separate manual queue).

## Layout

| Path | Why |
| --- | --- |
| [`plugin.json`](plugin.json) | Agent Plugins 1.0.0 (portable Open Plugin) |
| [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) | Cursor Plugin manifest |
| [`skills/grok-bot-marketplace/`](skills/grok-bot-marketplace/SKILL.md) | Catalog skill |
| [`skills/grok-bot-x-feed/`](skills/grok-bot-x-feed/SKILL.md) | X discovery skill |
| [`scripts/catalog.py`](scripts/catalog.py) | Marketplace CLI + `x-search` / `x-monitor` |
| [`scripts/x_feed.py`](scripts/x_feed.py) | X API client (also runnable standalone) |
| [`data/catalog.json`](data/catalog.json) | Catalog snapshot |
| [`.env.example`](.env.example) | Token template (copy to `.env`) |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

X tests mock HTTP. CI never calls X or needs a token.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `unrecognized arguments: --format` | Put `--format` after the subcommand, or pull latest (`x-search --format text`) |
| `X_BEARER_TOKEN is not set` | Export the token or copy `.env.example` → `.env`. Catalog commands do not need it |
| X HTTP 403 | App likely lacks recent-search / search Posts |
| X HTTP 401 | Token is wrong or revoked |
| X HTTP 429 | Rate/quota limit — wait and retry |
| Empty X results | Recent search is ~7 days; try a broader query |
| Marketplace refresh failed | HTML shape or a bot-challenge page — keep the snapshot and retry |
| `installCount` all zeros | Expected today; do not treat as unused |

## License

[MIT](LICENSE) — see [CHANGELOG.md](CHANGELOG.md).
