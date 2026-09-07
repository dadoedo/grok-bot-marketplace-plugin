#!/usr/bin/env python3
"""Build the public grokbots.store feed on hetzner-prod (operator job).

Scrapes the official Grok Bot marketplace HTML and (optionally) X API v2
recent search, then writes merged feed JSON:

    { marketplace, xViral, fetchedAt, sources }

Exit codes:
    0  success
    2  marketplace scrape/parse failed (hard — no write unless a previous file exists)
    3  X Bearer missing for live X
    4  X search failed (marketplace written; xViral empty unless --allow-x-failure)

Plugin users do not run this. They read https://grokbots.store/feed.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import catalog  # noqa: E402
import feed_client  # noqa: E402
import x_feed  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "feed.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scrape_marketplace() -> dict[str, Any]:
    html = catalog.fetch_url(catalog.MARKETPLACE_URL)
    templates = catalog.parse_templates(html)
    return catalog.build_catalog_document(templates)


def x_posts_live(*, max_results: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    token = x_feed.resolve_bearer_token()
    query = x_feed.build_query(None)
    posts, meta = x_feed.search_posts(
        query=query,
        token=token,
        max_results=max_results,
    )
    return posts, {"query": query, "meta": meta, "source": "x-api-v2-recent-search"}


def x_posts_demo() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = x_feed.load_demo_payload()
    posts, meta = x_feed.posts_from_demo_payload(raw)
    return posts, {
        "query": x_feed.DEFAULT_DISCOVERY_QUERY,
        "meta": meta,
        "source": "x-demo-fixture",
    }


def merge_feed(
    marketplace: dict[str, Any],
    posts: list[dict[str, Any]],
    *,
    x_info: dict[str, Any],
    x_error: str | None = None,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(marketplace, handle)
        tmp = Path(handle.name)
    try:
        posts = x_feed.join_catalog(posts, tmp)
    finally:
        tmp.unlink(missing_ok=True)
    posts = x_feed.sort_posts(posts, "engagement")
    x_viral = {
        "feed": "x",
        "source": x_info.get("source") or "x-api-v2-recent-search",
        "query": x_info.get("query"),
        "sort": "engagement",
        "demo": x_info.get("source") == "x-demo-fixture",
        "live": x_info.get("source") == "x-api-v2-recent-search" and not x_error,
        "fetchedAt": utc_now(),
        "resultCount": len(posts),
        "meta": x_info.get("meta") or {},
        "results": posts,
        "install": {
            "method": "grokbot-deeplink",
            "note": (
                "Install is only via addHref grokbot:// or the marketplace URL. "
                "X posts are a discovery feed — never POST an install API."
            ),
        },
    }
    sources: dict[str, Any] = {
        "marketplace": marketplace.get("source") or catalog.MARKETPLACE_CATALOG_URL,
        "x": x_viral["source"],
        "host": "hetzner-prod",
    }
    if x_error:
        sources["xError"] = x_error
    return {
        "marketplace": marketplace,
        "xViral": x_viral,
        "fetchedAt": utc_now(),
        "sources": sources,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operator job: scrape marketplace + X, write grokbots.store feed.json",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output feed JSON (default: data/feed.json)",
    )
    parser.add_argument(
        "--catalog-out",
        default=None,
        help="Also write marketplace snapshot JSON (optional)",
    )
    parser.add_argument(
        "--from-snapshot",
        action="store_true",
        help="Use data/catalog.json instead of live marketplace HTML",
    )
    parser.add_argument(
        "--demo-x",
        action="store_true",
        help="Use checked-in X fixture instead of live recent search",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        dest="max_results",
        help="X recent-search max_results (live only)",
    )
    parser.add_argument(
        "--allow-x-failure",
        action="store_true",
        help="If X search fails, still exit 0 after writing marketplace + empty xViral",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out)

    try:
        if args.from_snapshot:
            marketplace = catalog.load_catalog(ROOT / "data" / "catalog.json")
        else:
            marketplace = scrape_marketplace()
    except catalog.CatalogError as exc:
        print(json.dumps({"error": str(exc), "stage": "marketplace"}), file=sys.stderr)
        return 2

    x_error: str | None = None
    posts: list[dict[str, Any]] = []
    x_info: dict[str, Any] = {"source": "x-api-v2-recent-search"}
    x_failed = False

    if args.demo_x:
        try:
            posts, x_info = x_posts_demo()
        except x_feed.XFeedError as exc:
            x_error = str(exc)
            x_failed = True
            x_info = {"source": "x-demo-fixture"}
    else:
        try:
            posts, x_info = x_posts_live(max_results=args.max_results)
        except x_feed.XAuthError as exc:
            x_error = str(exc)
            x_failed = True
            if not args.allow_x_failure:
                feed = merge_feed(marketplace, [], x_info={"source": "x-api-v2-recent-search"}, x_error=x_error)
                write_json(out, feed)
                print(json.dumps({"error": x_error, "stage": "x-auth", "wrote": str(out)}), file=sys.stderr)
                return 3
        except x_feed.XFeedError as exc:
            x_error = str(exc)
            x_failed = True
            x_info = {"source": "x-api-v2-recent-search"}

    if x_failed and not args.demo_x:
        posts = []

    feed = merge_feed(marketplace, posts, x_info=x_info, x_error=x_error)
    write_json(out, feed)
    if args.catalog_out:
        write_json(Path(args.catalog_out), marketplace)

    summary = {
        "wrote": str(out),
        "botCount": marketplace.get("botCount"),
        "xResultCount": feed["xViral"]["resultCount"],
        "fetchedAt": feed["fetchedAt"],
        "xError": x_error,
    }
    print(json.dumps(summary, indent=2))

    if x_failed and not args.allow_x_failure:
        return 4 if "Bearer" not in (x_error or "") and "not set" not in (x_error or "") else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
