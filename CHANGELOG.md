# Changelog

## 0.2.0

- X discovery feed: `x-search` and `x-monitor` via official X API v2 recent search (`X_BEARER_TOKEN`)
- Join X posts to the marketplace catalog when a bot slug or grokbot:// template id matches
- Checkpoint file `data/x-checkpoint.json` for recurring monitor runs
- Hardened marketplace HTML fetch/parse errors and addHref fallback parser
- Document `installCount: 0` as non-signal
- Product README, `.env.example`, second skill for the X feed

## 0.1.0

- Marketplace catalog snapshot, list/search/compare/refresh
- grokbot:// install links only — no REST install API
