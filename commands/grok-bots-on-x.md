---
name: grok-bots-on-x
description: Search recent X posts that share Grok Bot marketplace or grokbot:// template links
---

Use the `grok-bot-x-feed` skill. Requires `X_BEARER_TOKEN`. From the plugin root:

```bash
python3 scripts/catalog.py x-search --format text
python3 scripts/catalog.py x-monitor
```

Read/search only. Do not post. Join hits to the catalog when a bot id matches.
