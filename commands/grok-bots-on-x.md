---
name: grok-bots-on-x
description: Show viral X posts that share Grok Bot marketplace or grokbot:// template links
---

Use the `grok-bot-x-feed` skill. From the plugin root:

```bash
python3 scripts/catalog.py x-viral --format text
python3 scripts/catalog.py x-search --offline
python3 scripts/catalog.py x-viral --demo --format text
```

Reads the public grokbots.store feed (`xViral`). No X API key. Read/search only. Do not post. Join hits to the catalog when a bot id matches. Label `feed: x` vs `feed: marketplace`.
