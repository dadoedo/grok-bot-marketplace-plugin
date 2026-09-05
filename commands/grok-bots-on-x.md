---
name: grok-bots-on-x
description: Search recent X posts that share Grok Bot marketplace or grokbot:// template links
---

Use the `grok-bot-x-feed` skill. From the plugin root:

```bash
python3 scripts/catalog.py x-viral --demo --format text
python3 scripts/catalog.py x-search --live --format text
python3 scripts/catalog.py x-monitor --live
```

`--demo` / no token → offline fixture. `--live` needs `X_BEARER_TOKEN`. Read/search only. Do not post. Join hits to the catalog when a bot id matches. Label `feed: x` vs `feed: marketplace`.
