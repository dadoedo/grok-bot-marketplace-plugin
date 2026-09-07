#!/usr/bin/env python3
"""Read the public grokbots.store feed (plugin path — no X credentials)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEED_URL = "https://grokbots.store/feed.json"
DEFAULT_FEED_SNAPSHOT = PLUGIN_ROOT / "data" / "feed.json"
DEFAULT_CATALOG_SNAPSHOT = PLUGIN_ROOT / "data" / "catalog.json"
DEFAULT_ENV_PATH = PLUGIN_ROOT / ".env"
USER_AGENT = (
    "grok-bot-marketplace-plugin/0.4 "
    "(+https://github.com/dadoedo/grok-bot-marketplace-plugin)"
)
OFFLINE_TRUTHY = frozenset({"1", "true", "yes", "on"})
UrlOpen = Callable[..., Any]


class FeedError(RuntimeError):
    """Hosted feed fetch or parse failure."""


def load_env_file(path: Path = DEFAULT_ENV_PATH, environ: dict[str, str] | None = None) -> None:
    env = environ if environ is not None else os.environ
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key and key not in env:
            env[key] = value


def resolve_feed_url(environ: dict[str, str] | None = None, explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    env = environ if environ is not None else os.environ
    load_env_file(DEFAULT_ENV_PATH, env)
    return (env.get("GROKBOTS_FEED_URL") or "").strip() or DEFAULT_FEED_URL


def offline_enabled(environ: dict[str, str] | None = None, flag: bool = False) -> bool:
    if flag:
        return True
    env = environ if environ is not None else os.environ
    load_env_file(DEFAULT_ENV_PATH, env)
    return (env.get("GROKBOTS_OFFLINE") or "").strip().lower() in OFFLINE_TRUTHY


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_x_viral(*, source: str = "none", demo: bool = False) -> dict[str, Any]:
    return {
        "feed": "x",
        "source": source,
        "demo": demo,
        "live": False,
        "resultCount": 0,
        "results": [],
    }


def wrap_catalog_as_feed(
    document: dict[str, Any],
    *,
    x_viral: dict[str, Any] | None = None,
    source: str = "snapshot",
) -> dict[str, Any]:
    return {
        "marketplace": document,
        "xViral": x_viral or empty_x_viral(source="snapshot"),
        "fetchedAt": document.get("fetchedAt") or utc_now(),
        "sources": {
            "marketplace": document.get("source") or str(DEFAULT_CATALOG_SNAPSHOT),
            "x": (x_viral or {}).get("source") or "snapshot",
            "dataSource": source,
        },
    }


def marketplace_document(feed: dict[str, Any]) -> dict[str, Any]:
    import catalog as catalog_mod

    raw = feed.get("marketplace")
    if isinstance(raw, dict) and isinstance(raw.get("bots"), list):
        document = dict(raw)
        if not isinstance(document.get("install"), dict):
            document["install"] = {
                "method": "grokbot-deeplink",
                "note": catalog_mod.INSTALL_NOTE,
            }
        document.setdefault("botCount", len(document["bots"]))
        document.setdefault("source", DEFAULT_FEED_URL)
        return document
    if isinstance(raw, list):
        return catalog_mod.build_catalog_document(raw, fetched_at=feed.get("fetchedAt"))
    raise FeedError("Feed marketplace section missing bots[]")


def x_viral_envelope(feed: dict[str, Any]) -> dict[str, Any]:
    raw = feed.get("xViral")
    if raw is None:
        return empty_x_viral()
    if isinstance(raw, list):
        posts = [p for p in raw if isinstance(p, dict)]
        return {
            "feed": "x",
            "source": (feed.get("sources") or {}).get("x") or "hosted-feed",
            "demo": False,
            "live": False,
            "resultCount": len(posts),
            "results": posts,
        }
    if isinstance(raw, dict):
        posts = raw.get("results") if isinstance(raw.get("results"), list) else []
        posts = [p for p in posts if isinstance(p, dict)]
        envelope = dict(raw)
        envelope.setdefault("feed", "x")
        envelope["results"] = posts
        envelope["resultCount"] = len(posts)
        envelope.setdefault("demo", False)
        envelope.setdefault("live", False)
        envelope.setdefault("source", (feed.get("sources") or {}).get("x") or "hosted-feed")
        return envelope
    raise FeedError("Feed xViral section is not an object or array")


def validate_feed(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FeedError("Feed JSON is not an object")
    marketplace_document(payload)
    x_viral_envelope(payload)
    payload.setdefault("fetchedAt", utc_now())
    payload.setdefault("sources", {})
    if not isinstance(payload["sources"], dict):
        payload["sources"] = {}
    return payload


def fetch_hosted_feed(
    url: str,
    *,
    timeout: int = 8,
    urlopen: UrlOpen | None = None,
) -> dict[str, Any]:
    opener = urlopen or urllib.request.urlopen
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read()
            status = int(getattr(resp, "status", None) or getattr(resp, "code", 200) or 200)
    except urllib.error.HTTPError as exc:
        raise FeedError(f"Failed to fetch {url} (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise FeedError(f"Failed to fetch {url}: {exc}") from exc
    except TimeoutError as exc:
        raise FeedError(f"Timed out fetching {url}") from exc
    if status >= 400:
        raise FeedError(f"Failed to fetch {url} (HTTP {status})")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FeedError(f"Feed at {url} is not valid JSON: {exc}") from exc
    feed = validate_feed(payload)
    sources = dict(feed.get("sources") or {})
    sources["dataSource"] = "hosted"
    sources["feedUrl"] = url
    feed["sources"] = sources
    return feed


def load_feed_snapshot(path: Path = DEFAULT_FEED_SNAPSHOT) -> dict[str, Any]:
    import catalog as catalog_mod

    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FeedError(f"Feed snapshot is not valid JSON: {exc}") from exc
        feed = validate_feed(payload)
        sources = dict(feed.get("sources") or {})
        sources["dataSource"] = "snapshot"
        feed["sources"] = sources
        return feed
    if DEFAULT_CATALOG_SNAPSHOT.is_file():
        document = catalog_mod.load_catalog(DEFAULT_CATALOG_SNAPSHOT)
        return wrap_catalog_as_feed(document, source="catalog-snapshot")
    raise FeedError(
        f"No feed snapshot at {path} and no catalog at {DEFAULT_CATALOG_SNAPSHOT}"
    )


def load_feed(
    *,
    feed_url: str | None = None,
    offline: bool = False,
    snapshot: Path = DEFAULT_FEED_SNAPSHOT,
    urlopen: UrlOpen | None = None,
) -> dict[str, Any]:
    """Hosted feed first; bundled snapshot on failure or --offline."""
    if offline:
        return load_feed_snapshot(snapshot)
    url = resolve_feed_url(explicit=feed_url)
    try:
        return fetch_hosted_feed(url, urlopen=urlopen)
    except FeedError:
        fallback = load_feed_snapshot(snapshot)
        sources = dict(fallback.get("sources") or {})
        sources["dataSource"] = "snapshot-fallback"
        sources["feedUrl"] = url
        fallback["sources"] = sources
        return fallback
