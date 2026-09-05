---
name: browse-grok-bots
description: List or search public Grok Bot marketplace templates and return grokbot:// install links
---

Use the `grok-bot-marketplace` skill. From the plugin root:

```bash
python3 scripts/catalog.py list --with-categories
python3 scripts/catalog.py search "seo" --format text
```

Always include addHref and marketplaceUrl. There is no install API.
