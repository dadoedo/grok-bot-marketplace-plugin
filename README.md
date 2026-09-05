# Grok Bot Marketplace

Cursor **Open Plugin** so agents can discover [Grok Bots](https://x.ai/bot/marketplace) two ways:

1. **Marketplace catalog** (`feed: marketplace`) — the public listing on x.ai (offline snapshot + optional live HTML refresh)
2. **X discovery feed** (`feed: x`) — recent posts that share marketplace / `grokbot://` template links (official X API v2)

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

`installCount` is returned when present. **Marketplace SSR currently ships `0` for every public bot** — that is honest, not “unused”. Do not rank by popularity until non-zero values appear.

## Quick start

```bash
git clone https://github.com/dadoedo/grok-bot-marketplace-plugin.git
cd grok-bot-marketplace-plugin

python3 scripts/catalog.py list --with-categories --format text
python3 scripts/catalog.py search "outbound" --category Sales --format text
python3 scripts/catalog.py compare researchy tinkabot

# X feed works offline against a checked-in fixture (no API key):
python3 scripts/catalog.py x-viral --demo --format text
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

Marketing page (GitHub Pages): [`site/`](site/) — working title **XBots** (temporary). Preview with `python3 -m http.server 8080 --directory site`. Enable Pages via GitHub Actions (see [`site/README.md`](site/README.md)); the branch UI cannot serve `/site`.

## Two feeds

JSON envelopes and cards are labeled so marketplace and X results are never mixed up:

| `feed` | Command | Needs network | Needs `X_BEARER_TOKEN` |
| --- | --- | --- | --- |
| `marketplace` | `list` `search` `compare` `show` `categories` | only `refresh` / `--details` | no |
| `x` | `x-search` `x-viral` / `x-trending` `x-monitor` | live only | live only (`--live`) |

X commands **default to the demo fixture** when no token is set (exit 0, setup JSON on stderr). Pass `--live` to require a real Bearer token (exit 3 with setup if missing).

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

Detected share links:

- `https://x.ai/bot/marketplace/bots/…`
- `https://x.ai/bot/marketplace` (listing)
- `grokbot://app/v1/bot-template?id=…`
- recognizable public `bot-template` / share URLs on x.ai

### Offline / demo mode (no key)

Checked-in fixture: [`data/demo/x-search-recent.json`](data/demo/x-search-recent.json) (same shape as X recent-search JSON).

```bash
python3 scripts/catalog.py x-search --demo --format text
python3 scripts/catalog.py x-viral --demo
python3 scripts/catalog.py x-trending --demo --format json
X_DEMO=1 python3 scripts/catalog.py x-monitor
```

`--demo` and `X_DEMO=1` never call the network. Demo runs do **not** write `data/x-checkpoint.json`.

If `X_BEARER_TOKEN` is unset and you did **not** pass `--live`, the same fixture is used automatically. Stderr prints a JSON setup payload (`demoFallback: true`); stdout is a normal `feed: x` result with `"demo": true`. Marketplace commands are unaffected.

### Live credentials

App-only Bearer is enough for public recent search. User-context OAuth is not required.

1. Create a Project + App at [developer.x.com](https://developer.x.com) (X Developer Portal).
2. Give the app **read** access. Recent search typically needs X API Basic (or higher) with **search Posts**.
3. Open **Keys and tokens** and copy the **Bearer Token** (not the API Key / API Secret).
4. Keep it out of git:

```bash
cp .env.example .env          # .env is gitignored
# paste: X_BEARER_TOKEN=your-token

# or for this shell only:
export X_BEARER_TOKEN='YOUR_TOKEN'
```

Accepted names (first non-empty wins):

| Variable | Role |
| --- | --- |
| `X_BEARER_TOKEN` | recommended |
| `TWITTER_BEARER_TOKEN` | alias |
| `X_API_BEARER_TOKEN` | alias |
| `X_DEMO=1` | force offline fixture (same as `--demo`) |

A plugin-root `.env` is loaded with the stdlib (no python-dotenv). **Existing process env wins.** Tokens are never logged or written to the catalog / checkpoint.

```bash
python3 scripts/catalog.py x-search --live --format text
python3 scripts/catalog.py x-viral --live "researchy"
python3 scripts/catalog.py x-monitor --live
```

`--live` with no token exits `3` and prints setup JSON on stderr.

### Search, viral, monitor

```bash
python3 scripts/catalog.py x-search --format text
python3 scripts/catalog.py x-search "researchy" --sort engagement
python3 scripts/catalog.py x-viral
python3 scripts/catalog.py x-trending --demo
python3 scripts/catalog.py x-monitor
python3 scripts/x_feed.py search --max-results 50
python3 scripts/x_feed.py viral --demo
```

Default query matches:

- `x.ai/bot/marketplace`
- `grokbot://app/v1/bot-template`
- `"Grok Bot"` + marketplace / template / share

Extra keywords are ANDed with that filter unless the query already looks like an X search (`x.ai`, `grokbot`, `url:`).

Each hit includes post URL, author, text, public metrics, extracted marketplace / `grokbot://` / share links, `feed: x`, and **joined catalog cards** (`feed: marketplace`) when a bot slug or template id matches the snapshot. Unknown shares stay raw cards (still with whatever links were in the post).

`x-viral` / `x-trending` force engagement ranking (likes, reposts, quotes, replies). `x-search` defaults to engagement; `x-monitor` defaults to recent.

`x-monitor` stores the newest tweet id in `data/x-checkpoint.json` and passes it as `since_id` next time (**live only**). `--reset` ignores the checkpoint. Recent search only covers about **seven days**.

## Install the plugin

### cursor.directory (community — publish path)

1. After merge, submit this GitHub repo at [cursor.directory/plugins/new](https://cursor.directory/plugins/new).
2. Users find **Grok Bot Marketplace** on [cursor.directory](https://cursor.directory) and install it.

The repo is a single plugin at the root: Agent Plugins `plugin.json` plus Cursor `.cursor-plugin/plugin.json`, skills under `skills/*/SKILL.md`.

Publish notes:

- Keep secrets out of the repo (never commit `.env`).
- Demo mode means reviewers can exercise the X feed without an X API key.
- Skills + CLI are the interface; there is no install API to document.

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
| [`scripts/catalog.py`](scripts/catalog.py) | Marketplace CLI + `x-search` / `x-viral` / `x-monitor` |
| [`scripts/x_feed.py`](scripts/x_feed.py) | X API client (also runnable standalone) |
| [`data/catalog.json`](data/catalog.json) | Catalog snapshot |
| [`data/demo/x-search-recent.json`](data/demo/x-search-recent.json) | Offline X feed fixture |
| [`site/`](site/) | GitHub Pages landing (working title XBots) |
| [`.env.example`](.env.example) | Token template (copy to `.env`) |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

X tests mock HTTP and exercise `--demo` / missing-token fallback. CI never calls X or needs a token.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `unrecognized arguments: --format` | Put `--format` after the subcommand, or pull latest (`x-search --format text`) |
| `X_BEARER_TOKEN is not set` | Expected without a key: demo fixture is used. For live data, export the token or copy `.env.example` → `.env`, then pass `--live` |
| `--live` exits 3 | Token missing or rejected. Catalog commands do not need it |
| X HTTP 403 | App likely lacks recent-search / search Posts |
| X HTTP 401 | Token is wrong or revoked |
| X HTTP 429 | Rate/quota limit — wait and retry |
| Empty X results | Recent search is ~7 days; try a broader query |
| Marketplace refresh failed | HTML shape or a bot-challenge page — keep the snapshot and retry |
| `installCount` all zeros | Expected today; do not treat as unused |

## License

[MIT](LICENSE) — see [CHANGELOG.md](CHANGELOG.md).
