#!/usr/bin/env python3
"""Copy a slim marketplace catalog into site/catalog.json for the landing page."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "catalog.json"
DEST = ROOT / "site" / "catalog.json"
FIELDS = (
    "id",
    "name",
    "creatorName",
    "handle",
    "summary",
    "description",
    "categories",
    "color",
    "shape",
    "imageUrl",
    "addHref",
    "marketplaceUrl",
)


def main() -> int:
    document = json.loads(SRC.read_text(encoding="utf-8"))
    bots = []
    for raw in document.get("bots") or []:
        bots.append({key: raw.get(key) for key in FIELDS})
    payload = {
        "source": document.get("source"),
        "fetchedAt": document.get("fetchedAt"),
        "botCount": document.get("botCount") or len(bots),
        "categories": document.get("categories") or [],
        "install": document.get("install"),
        "bots": bots,
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(bots)} bots → {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
