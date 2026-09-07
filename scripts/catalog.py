#!/usr/bin/env python3
"""Browse the public Grok Bot marketplace catalog.

There is no public marketplace REST API. This tool scrapes the SSR HTML at
https://x.ai/bot/marketplace (anchor #marketplace-catalog), where the full
catalog is embedded in the Next.js flight payload.

Install is only via each bot's addHref (grokbot://app/v1/bot-template?id=…).
Never call a fake install endpoint. Return addHref + marketplaceUrl for the
user to open.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = PLUGIN_ROOT / "data" / "catalog.json"
DEFAULT_FEED_URL = "https://grokbots.store/feed.json"
MARKETPLACE_URL = "https://x.ai/bot/marketplace"
MARKETPLACE_CATALOG_URL = f"{MARKETPLACE_URL}#marketplace-catalog"
BOT_PAGE_URL = MARKETPLACE_URL + "/bots/{id}"
USER_AGENT = (
    "grok-bot-marketplace-plugin/0.4 "
    "(+https://github.com/dadoedo/grok-bot-marketplace-plugin)"
)
INSTALL_NOTE = (
    "There is no public Bot marketplace REST API. Install is only via the "
    "addHref grokbot:// deep link (or the marketplace URL) — open it in Grok Bot. "
    "Do not POST or invent an install endpoint."
)

NEXT_F_PUSH = re.compile(
    r"self\.__next_f\.push\(\[1,(\"(?:\\.|[^\"\\])*\")\]\)"
)

DETAIL_LIST_FIELDS = ("memories", "skills", "routines", "integrations")


class CatalogError(RuntimeError):
    """Catalog fetch or parse failure."""


def _json_value_at_generic(src: str, start: int) -> str:
    """Brace-match an object or array, tracking both {} and []."""
    if start >= len(src) or src[start] not in "{[":
        raise CatalogError("Expected JSON object or array in page payload")
    stack: list[str] = []
    in_str = False
    esc = False
    pairs = {"{": "}", "[": "]"}
    for i, ch in enumerate(src[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch in "{[":
            stack.append(pairs[ch])
        elif ch in "}]":
            if not stack or stack[-1] != ch:
                raise CatalogError("Mismatched JSON brackets in page payload")
            stack.pop()
            if not stack:
                return src[start : i + 1]
    raise CatalogError("Unclosed JSON value in page payload")


def flight_text(html: str) -> str:
    """Concatenate Next.js ``self.__next_f`` string payloads."""
    parts = [json.loads(m.group(1)) for m in NEXT_F_PUSH.finditer(html)]
    if not parts:
        raise CatalogError(
            "No Next.js flight payload found. The marketplace HTML shape may have changed."
        )
    return "".join(parts)


def _find_json_key(text: str, key: str) -> int:
    """Return the index of a JSON value after ``"key":``, allowing whitespace."""
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:')
    match = pattern.search(text)
    if not match:
        return -1
    i = match.end()
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def parse_templates(html: str) -> list[dict[str, Any]]:
    """Extract the embedded ``templates`` array from marketplace HTML."""
    try:
        text = flight_text(html)
    except CatalogError:
        text = ""
    templates: list[dict[str, Any]] = []
    if text:
        value_at = _find_json_key(text, "templates")
        if value_at >= 0:
            try:
                raw = _json_value_at_generic(text, value_at)
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    templates = [item for item in parsed if isinstance(item, dict)]
            except (CatalogError, json.JSONDecodeError):
                templates = []
        if not templates:
            templates = _templates_from_addhref(text)
    if not templates:
        raise CatalogError(
            "No templates array in marketplace payload. "
            "The catalog embed may have changed, or the HTML was not the marketplace page."
        )
    return templates


def _templates_from_addhref(text: str) -> list[dict[str, Any]]:
    """Fallback: collect bot objects that already have a grokbot:// addHref."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    search_from = 0
    while True:
        idx = text.find('"addHref"', search_from)
        if idx < 0:
            break
        start = text.rfind("{", 0, idx)
        while start >= 0:
            try:
                obj = json.loads(_json_value_at_generic(text, start))
            except (CatalogError, json.JSONDecodeError):
                start = text.rfind("{", 0, start)
                continue
            href = str(obj.get("addHref") or "") if isinstance(obj, dict) else ""
            bot_id = str(obj.get("id") or "") if isinstance(obj, dict) else ""
            if href.startswith("grokbot://") and bot_id and bot_id not in seen:
                seen.add(bot_id)
                found.append(obj)
                break
            start = text.rfind("{", 0, start)
        search_from = idx + 1
    return found


def parse_bot_detail(html: str, bot_id: str | None = None) -> dict[str, Any]:
    """Extract one bot object from a detail page payload."""
    text = flight_text(html)
    search_from = 0
    while True:
        idx = text.find('"addHref"', search_from)
        if idx < 0:
            break
        start = text.rfind("{", 0, idx)
        found = None
        while start >= 0:
            try:
                raw = _json_value_at_generic(text, start)
                obj = json.loads(raw)
            except (CatalogError, json.JSONDecodeError):
                start = text.rfind("{", 0, start)
                continue
            if isinstance(obj, dict) and obj.get("addHref") and obj.get("id"):
                if bot_id is None or obj.get("id") == bot_id:
                    found = obj
                    break
            start = text.rfind("{", 0, start)
        if found:
            return found
        search_from = idx + 1
    raise CatalogError("Could not parse bot detail object from page payload")


def marketplace_url_for(bot_id: str) -> str:
    return BOT_PAGE_URL.format(id=bot_id)


def normalize_bot(raw: dict[str, Any], *, include_details: bool = False) -> dict[str, Any]:
    bot_id = str(raw.get("id") or "").strip()
    if not bot_id:
        raise CatalogError("Bot record missing id")
    description = (raw.get("description") or raw.get("summary") or "") or ""
    summary = (raw.get("summary") or raw.get("description") or "") or ""
    categories = raw.get("categories") or []
    if not isinstance(categories, list):
        categories = [str(categories)]
    categories = [str(c) for c in categories if c]
    install_count = raw.get("installCount")
    if install_count is not None:
        try:
            install_count = int(install_count)
        except (TypeError, ValueError):
            install_count = None
    bot = {
        "id": bot_id,
        "name": str(raw.get("name") or ""),
        "creatorName": str(raw.get("creatorName") or ""),
        "handle": str(raw.get("handle") or ""),
        "description": str(description),
        "summary": str(summary),
        "categories": categories,
        "installCount": install_count,
        "color": raw.get("color"),
        "shape": raw.get("shape"),
        "imageUrl": raw.get("imageUrl") or None,
        "addHref": str(raw.get("addHref") or ""),
        "marketplaceUrl": marketplace_url_for(bot_id),
    }
    if include_details:
        instructions = raw.get("instructions") or ""
        bot["instructions"] = str(instructions) if instructions else ""
        bot["memories"] = _summarize_named(raw.get("memories") or [], "description")
        bot["skills"] = _summarize_named(raw.get("skills") or [], "description")
        bot["routines"] = _summarize_named(raw.get("routines") or [], "summary")
        bot["integrations"] = _summarize_named(raw.get("integrations") or [], "description")
    return bot


def _summarize_named(items: Iterable[Any], text_key: str, limit: int = 400) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get(text_key) or item.get("content") or item.get("description") or "")
        if len(text) > limit:
            text = text[: limit - 1].rstrip() + "…"
        out.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "text": text,
            }
        )
    return out


CARD_FIELDS = (
    "id",
    "name",
    "creator",
    "handle",
    "description",
    "categories",
    "installCount",
    "marketplaceUrl",
    "addHref",
)


def public_card(bot: dict[str, Any]) -> dict[str, Any]:
    """Fields skills/tools must return for list/search/compare."""
    bot_id = str(bot.get("id") or "")
    card = {
        "id": bot_id,
        "name": str(bot.get("name") or ""),
        "creator": str(bot.get("creatorName") or ""),
        "handle": str(bot.get("handle") or ""),
        "description": str(bot.get("summary") or bot.get("description") or ""),
        "categories": list(bot.get("categories") or []),
        "installCount": bot.get("installCount"),
        "marketplaceUrl": str(bot.get("marketplaceUrl") or marketplace_url_for(bot_id)),
        "addHref": str(bot.get("addHref") or ""),
        "feed": "marketplace",
        "source": "marketplace",
    }
    for key in DETAIL_LIST_FIELDS:
        if key in bot:
            card[key] = bot[key]
    if bot.get("instructions"):
        card["instructions"] = bot["instructions"]
    if bot.get("detailsError"):
        card["detailsError"] = bot["detailsError"]
    return card


def fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", None) or getattr(resp, "code", 200) or 200)
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", errors="replace")[:180]
        except Exception:
            snippet = ""
        extra = f" Body starts with: {snippet!r}" if snippet else ""
        raise CatalogError(
            f"Failed to fetch {url} (HTTP {exc.code}). "
            f"Expected the public marketplace HTML catalog.{extra}"
        ) from exc
    except urllib.error.URLError as exc:
        raise CatalogError(f"Failed to fetch {url}: {exc}") from exc
    lowered = body.lower()
    if "self.__next_f" not in body and "<html" not in lowered:
        raise CatalogError(
            f"Unexpected response from {url} (HTTP {status}, {len(body)} bytes). "
            "Expected marketplace HTML with an embedded Next.js catalog payload."
        )
    if "cf-browser-verification" in lowered or "just a moment" in lowered:
        raise CatalogError(
            f"Marketplace HTML from {url} looks like a bot challenge, not the catalog."
        )
    return body


def build_catalog_document(templates: list[dict[str, Any]], *, fetched_at: str | None = None) -> dict[str, Any]:
    bots = [normalize_bot(t) for t in templates]
    bots.sort(key=lambda b: (b["name"] or "").lower())
    categories: dict[str, int] = {}
    for bot in bots:
        for cat in bot["categories"]:
            categories[cat] = categories.get(cat, 0) + 1
    return {
        "source": MARKETPLACE_CATALOG_URL,
        "fetchedAt": fetched_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "botCount": len(bots),
        "categories": [
            {"name": name, "count": categories[name]}
            for name in sorted(categories, key=lambda n: (-categories[n], n.lower()))
        ],
        "install": {
            "method": "grokbot-deeplink",
            "note": INSTALL_NOTE,
        },
        "bots": bots,
    }


def refresh_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    html = fetch_url(MARKETPLACE_URL)
    templates = parse_templates(html)
    document = build_catalog_document(templates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return document


def catalog_path_is_explicit(path: Path) -> bool:
    try:
        return path.resolve() != DEFAULT_CATALOG_PATH.resolve()
    except OSError:
        return str(path) != str(DEFAULT_CATALOG_PATH)


def load_marketplace_for_cli(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    """Hosted grokbots.store feed by default; snapshot if --offline or --catalog."""
    import feed_client

    offline = feed_client.offline_enabled(flag=bool(getattr(args, "offline", False)))
    path = Path(args.catalog)
    if offline or catalog_path_is_explicit(path):
        return load_catalog(path), "snapshot"
    feed = feed_client.load_feed(feed_url=getattr(args, "feed_url", None), offline=False)
    document = feed_client.marketplace_document(feed)
    source = str((feed.get("sources") or {}).get("dataSource") or "hosted")
    return document, source


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise CatalogError(
            f"No catalog snapshot at {path}. Run: python3 scripts/catalog.py refresh "
            "or python3 ops/refresh_feed.py --from-snapshot --demo-x"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Catalog snapshot is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("bots"), list):
        raise CatalogError("Catalog snapshot missing bots[]")
    return document


def _haystack(bot: dict[str, Any]) -> str:
    parts = [
        bot.get("id") or "",
        bot.get("name") or "",
        bot.get("creatorName") or "",
        bot.get("handle") or "",
        bot.get("description") or "",
        bot.get("summary") or "",
        " ".join(bot.get("categories") or []),
    ]
    return " ".join(parts).lower()


def filter_bots(
    bots: list[dict[str, Any]],
    *,
    query: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    results = bots
    if category:
        needle = category.strip().lower()
        if needle:
            exact = [
                b
                for b in results
                if any(needle == c.lower() for c in (b.get("categories") or []))
            ]
            results = exact or [
                b
                for b in results
                if any(needle in c.lower() for c in (b.get("categories") or []))
            ]
    if query:
        tokens = [t for t in query.lower().split() if t]
        results = [b for b in results if all(tok in _haystack(b) for tok in tokens)]
    return results


def sort_bots(bots: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "installs":
        return sorted(
            bots,
            key=lambda b: (
                -(b.get("installCount") or 0),
                (b.get("name") or "").lower(),
            ),
        )
    return sorted(bots, key=lambda b: (b.get("name") or "").lower())


def find_bots(bots: list[dict[str, Any]], identifiers: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {b["id"].lower(): b for b in bots}
    by_name = {}
    for b in bots:
        by_name.setdefault((b.get("name") or "").lower(), []).append(b)
    found: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[str] = set()
    for ident in identifiers:
        key = ident.strip().lower()
        if not key:
            continue
        match = by_id.get(key)
        if match is None:
            names = by_name.get(key) or []
            match = names[0] if len(names) == 1 else None
            if match is None and len(names) > 1:
                missing.append(f"{ident} (ambiguous name; use id)")
                continue
        if match is None:
            # prefix / substring on id or name
            hits = [
                b
                for b in bots
                if key == (b.get("handle") or "").lower()
                or key in b["id"].lower()
                or key in (b.get("name") or "").lower()
            ]
            if len(hits) == 1:
                match = hits[0]
            elif len(hits) > 1:
                missing.append(f"{ident} (ambiguous; use id)")
                continue
        if match is None:
            missing.append(ident)
            continue
        if match["id"] in seen:
            continue
        seen.add(match["id"])
        found.append(match)
    return found, missing


def fetch_details(bot: dict[str, Any]) -> dict[str, Any]:
    html = fetch_url(marketplace_url_for(bot["id"]))
    raw = parse_bot_detail(html, bot["id"])
    detailed = normalize_bot(raw, include_details=True)
    # Prefer live addHref/description when present; keep snapshot fallbacks.
    merged = dict(bot)
    merged.update(detailed)
    return merged


def envelope(
    document: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "source": document.get("source") or MARKETPLACE_CATALOG_URL,
        "feed": "marketplace",
        "fetchedAt": document.get("fetchedAt"),
        "botCount": document.get("botCount"),
        "resultCount": len(results),
        "install": document.get("install")
        or {"method": "grokbot-deeplink", "note": INSTALL_NOTE},
        "results": [public_card(b) for b in results],
    }
    if extra:
        payload.update(extra)
    return payload


def print_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def print_text_cards(payload: dict[str, Any]) -> None:
    print(f"Source: {payload.get('source')}  (fetched {payload.get('fetchedAt')})")
    print(f"feed: marketplace")
    print(f"Results: {payload.get('resultCount')} / {payload.get('botCount')} bots in snapshot")
    print(INSTALL_NOTE)
    print()
    for bot in payload.get("results") or []:
        cats = ", ".join(bot.get("categories") or []) or "—"
        installs = bot.get("installCount")
        installs_s = "n/a" if installs is None else str(installs)
        handle = f" @{bot['handle']}" if bot.get("handle") else ""
        print(f"- {bot.get('name')} — {bot.get('creator')}{handle}")
        print(f"  {bot.get('description')}")
        print(f"  categories: {cats}  installs: {installs_s}  id: {bot.get('id')}")
        print(f"  marketplace: {bot.get('marketplaceUrl')}")
        print(f"  addHref: {bot.get('addHref')}")
        if bot.get("instructions"):
            print(f"  instructions: {bot['instructions'][:500]}")
        for group in DETAIL_LIST_FIELDS:
            items = bot.get(group) or []
            if not items:
                continue
            print(f"  {group}:")
            for item in items:
                text = item.get("text") or ""
                print(f"    - {item.get('name')}: {text[:240]}")
        print()


def cmd_refresh(args: argparse.Namespace) -> int:
    path = Path(args.catalog)
    document = refresh_catalog(path)
    extra = {"wrote": str(path), "categories": document.get("categories")}
    payload = envelope(document, document["bots"] if args.list else [], extra=extra)
    if not args.list:
        payload.pop("results", None)
        payload["resultCount"] = 0
    _emit(payload, args.format)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    document, data_source = load_marketplace_for_cli(args)
    bots = filter_bots(document["bots"], category=args.category)
    bots = sort_bots(bots, args.sort)
    if args.limit is not None:
        bots = bots[: args.limit]
    extra: dict[str, Any] = {"dataSource": data_source}
    if args.with_categories:
        extra["categories"] = document.get("categories")
    _emit(envelope(document, bots, extra=extra), args.format)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    document, data_source = load_marketplace_for_cli(args)
    bots = filter_bots(document["bots"], query=args.query, category=args.category)
    bots = sort_bots(bots, args.sort)
    if args.limit is not None:
        bots = bots[: args.limit]
    _emit(
        envelope(
            document,
            bots,
            extra={"query": args.query, "category": args.category, "dataSource": data_source},
        ),
        args.format,
    )
    return 0


def cmd_categories(args: argparse.Namespace) -> int:
    document, data_source = load_marketplace_for_cli(args)
    payload = {
        "source": document.get("source"),
        "feed": "marketplace",
        "fetchedAt": document.get("fetchedAt"),
        "botCount": document.get("botCount"),
        "categories": document.get("categories") or [],
        "install": document.get("install"),
        "dataSource": data_source,
    }
    _emit(payload, args.format)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    document, data_source = load_marketplace_for_cli(args)
    found, missing = find_bots(document["bots"], args.ids)
    if args.details:
        found = [_safe_details(b) for b in found]
    extra: dict[str, Any] = {"dataSource": data_source}
    if missing:
        extra["missing"] = missing
    _emit(envelope(document, found, extra=extra), args.format)
    return 1 if missing and not found else 0


def cmd_compare(args: argparse.Namespace) -> int:
    document, data_source = load_marketplace_for_cli(args)
    found, missing = find_bots(document["bots"], args.ids)
    if args.details:
        found = [_safe_details(b) for b in found]
    extra = {"dataSource": data_source}
    if missing:
        extra["missing"] = missing
    _emit(envelope(document, found, extra=extra), args.format)
    return 1 if missing and not found else 0


def _safe_details(bot: dict[str, Any]) -> dict[str, Any]:
    try:
        return fetch_details(bot)
    except CatalogError as exc:
        failed = dict(bot)
        failed["detailsError"] = str(exc)
        return failed


def _emit(payload: dict[str, Any], fmt: str) -> None:
    if fmt == "text":
        if "results" in payload:
            print_text_cards(payload)
        else:
            print_json(payload)
        return
    print_json(payload)


def _shared_cli_flags() -> argparse.ArgumentParser:
    """Flags that work before or after the subcommand (argparse parents).

    Defaults are SUPPRESS so a flag parsed on the parent is not reset to the
    subparser default (classic store_true / default overwrite bug).
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--catalog",
        default=argparse.SUPPRESS,
        help="Path to catalog snapshot JSON (default: data/catalog.json)",
    )
    shared.add_argument(
        "--format",
        choices=("json", "text"),
        default=argparse.SUPPRESS,
        help="Output format (json for agents, text for humans). Default: json.",
    )
    shared.add_argument(
        "--feed-url",
        dest="feed_url",
        default=argparse.SUPPRESS,
        help="Hosted feed JSON URL (default: GROKBOTS_FEED_URL or https://grokbots.store/feed.json)",
    )
    shared.add_argument(
        "--offline",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Skip the hosted feed; use --catalog / bundled snapshot only",
    )
    return shared


def finalize_cli_args(args: argparse.Namespace) -> argparse.Namespace:
    if not hasattr(args, "catalog"):
        args.catalog = str(DEFAULT_CATALOG_PATH)
    if not hasattr(args, "format"):
        args.format = "json"
    if not hasattr(args, "feed_url"):
        args.feed_url = None
    args.offline = bool(getattr(args, "offline", False))
    return args


def build_parser() -> argparse.ArgumentParser:
    shared = _shared_cli_flags()
    parser = argparse.ArgumentParser(
        description="Browse Grok Bots from the public grokbots.store feed "
        "(marketplace + X viral). Install is via grokbot:// addHref only — no REST install API.",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", parents=[shared], help="List bots from the hosted feed (snapshot fallback)")
    p_list.add_argument(
        "--category",
        help="Filter by category (case-insensitive exact match, then substring fallback)",
    )
    p_list.add_argument("--limit", type=int, default=None)
    p_list.add_argument("--sort", choices=("name", "installs"), default="name")
    p_list.add_argument("--with-categories", action="store_true", help="Include category counts")
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser(
        "search",
        parents=[shared],
        help="Search by keyword (name, creator, description, category)",
    )
    p_search.add_argument("query")
    p_search.add_argument(
        "--category",
        help="Also filter by category (exact match first, then substring)",
    )
    p_search.add_argument("--limit", type=int, default=None)
    p_search.add_argument("--sort", choices=("name", "installs"), default="name")
    p_search.set_defaults(func=cmd_search)

    p_cats = sub.add_parser("categories", parents=[shared], help="List category names and counts")
    p_cats.set_defaults(func=cmd_categories)

    p_show = sub.add_parser(
        "show",
        parents=[shared],
        help="Show one or more bots by id, name, or handle",
    )
    p_show.add_argument("ids", nargs="+")
    p_show.add_argument(
        "--details",
        action="store_true",
        help="Fetch each bot's marketplace detail page (instructions/memories/skills when present)",
    )
    p_show.set_defaults(func=cmd_show)

    p_cmp = sub.add_parser("compare", parents=[shared], help="Compare a few bots side by side")
    p_cmp.add_argument("ids", nargs="+")
    p_cmp.add_argument(
        "--details",
        action="store_true",
        help="Fetch detail pages so compare can include instructions/memories/skills",
    )
    p_cmp.set_defaults(func=cmd_compare)

    p_refresh = sub.add_parser(
        "refresh",
        parents=[shared],
        help="Operator helper: fetch live marketplace HTML and rewrite data/catalog.json "
        "(prefer ops/refresh_feed.py on hetzner-prod)",
    )
    p_refresh.add_argument(
        "--list",
        action="store_true",
        help="Include full bot list in the refresh response",
    )
    p_refresh.set_defaults(func=cmd_refresh)

    import x_feed

    p_xs = sub.add_parser(
        "x-search",
        parents=[shared],
        help="Viral/shared Grok Bot posts from the hosted feed "
        "(--demo fixture; --live is operator X API, not the product path)",
    )
    x_feed.add_x_arguments(p_xs)
    p_xs.set_defaults(func=x_feed.cmd_search, sort="engagement")

    p_xv = sub.add_parser(
        "x-viral",
        aliases=["x-trending"],
        parents=[shared],
        help="Hosted xViral ranked by engagement (--demo fixture; --live operator X API)",
    )
    x_feed.add_x_arguments(p_xv)
    p_xv.set_defaults(func=x_feed.cmd_viral, sort="engagement")

    p_xm = sub.add_parser(
        "x-monitor",
        parents=[shared],
        help="Operator: live X since checkpoint (--live). Product path is hosted xViral."
    )
    x_feed.add_x_arguments(p_xm)
    p_xm.set_defaults(func=x_feed.cmd_monitor, sort="recent")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = finalize_cli_args(parser.parse_args(argv))
    try:
        return int(args.func(args))
    except CatalogError as exc:
        print(json.dumps({"error": str(exc), "install": {"note": INSTALL_NOTE}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
