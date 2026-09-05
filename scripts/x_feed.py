#!/usr/bin/env python3
"""Discover Grok Bot template shares on X (read/search only).

Uses official X API v2 recent search with an app-only Bearer token.
Does not post. Does not call any marketplace install API.

Auth: set X_BEARER_TOKEN (aliases: TWITTER_BEARER_TOKEN, X_API_BEARER_TOKEN).
Optional local `.env` in the plugin root is loaded with stdlib only; existing
process env wins. Never logs or writes the token.

Offline: ``--demo`` / ``X_DEMO=1`` (and missing-token fallback) reads
``data/demo/x-search-recent.json``. ``--live`` requires a real token.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = PLUGIN_ROOT / "data" / "catalog.json"
DEFAULT_CHECKPOINT_PATH = PLUGIN_ROOT / "data" / "x-checkpoint.json"
DEFAULT_ENV_PATH = PLUGIN_ROOT / ".env"
DEFAULT_DEMO_PATH = PLUGIN_ROOT / "data" / "demo" / "x-search-recent.json"
FIXTURE_DEMO_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "x-search-recent.json"
X_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
USER_AGENT = (
    "grok-bot-marketplace-plugin/0.3 "
    "(+https://github.com/dadoedo/grok-bot-marketplace-plugin)"
)
TOKEN_ENV_NAMES = (
    "X_BEARER_TOKEN",
    "TWITTER_BEARER_TOKEN",
    "X_API_BEARER_TOKEN",
)
DEMO_TRUTHY = frozenset({"1", "true", "yes", "on"})
# Recent search is the last ~7 days. Keep the default query under 512 chars.
DEFAULT_DISCOVERY_QUERY = (
    '("x.ai/bot/marketplace" OR url:x.ai/bot OR '
    '"grokbot://app/v1/bot-template" OR '
    '("Grok Bot" (marketplace OR template OR share)))'
)
SETUP_HINT = (
    "X search needs an app-only Bearer token from https://developer.x.com "
    "(Developer Console → your App → Keys and tokens). "
    "export X_BEARER_TOKEN='…' or copy .env.example to .env. "
    "Without a token, x-* commands use the offline demo fixture "
    "(pass --live to require credentials). "
    "Marketplace list/search/compare still work without X."
)

MARKETPLACE_BOT_RE = re.compile(
    r"https?://(?:www\.)?x\.ai/bot/marketplace/bots/([A-Za-z0-9_-]+)",
    re.I,
)
MARKETPLACE_LISTING_RE = re.compile(
    r"https?://(?:www\.)?x\.ai/bot/marketplace(?:/|\b|[?#])",
    re.I,
)
GROKBOT_HREF_RE = re.compile(
    r"grokbot://app/v1/bot-template\?id=([A-Za-z0-9_-]+)",
    re.I,
)
GROKBOT_URL_RE = re.compile(r"grokbot://[^\s)>\"]+", re.I)
SHARE_TEMPLATE_RE = re.compile(
    r"https?://(?:www\.)?(?:x\.ai|grok\.com)/(?:bot/)?(?:marketplace/)?(?:share|template|bot-template)[^\s)>\"]*",
    re.I,
)
TEMPLATE_ID_QUERY_RE = re.compile(
    r"(?:grokbot://[^\s]*|[?&])id=([A-Za-z0-9_-]+)",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s)>\"]+", re.I)

UrlOpen = Callable[..., Any]


class XFeedError(RuntimeError):
    """X feed fetch/parse failure."""


class XAuthError(XFeedError):
    """Missing or rejected Bearer token."""


def load_env_file(path: Path = DEFAULT_ENV_PATH, environ: dict[str, str] | None = None) -> None:
    """Load KEY=VALUE lines into environ without overriding existing keys."""
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


def resolve_bearer_token(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    load_env_file(DEFAULT_ENV_PATH, env)
    for name in TOKEN_ENV_NAMES:
        value = (env.get(name) or "").strip()
        if value:
            return value
    raise XAuthError(
        "X_BEARER_TOKEN is not set. " + SETUP_HINT
    )


def auth_error_payload(message: str, *, demo_fallback: bool = False) -> dict[str, Any]:
    return {
        "error": message,
        "demoFallback": demo_fallback,
        "setup": {
            "env": "X_BEARER_TOKEN",
            "aliases": list(TOKEN_ENV_NAMES[1:]),
            "hint": SETUP_HINT,
            "example": "cp .env.example .env  # then paste the token",
            "portal": "https://developer.x.com",
            "docs": "https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent",
            "demo": "python3 scripts/catalog.py x-viral --demo --format json",
            "live": "python3 scripts/catalog.py x-search --live --format json",
        },
        "marketplaceStillWorks": True,
        "demo": {
            "flag": "--demo",
            "env": "X_DEMO=1",
            "fixture": "data/demo/x-search-recent.json",
        },
    }


def demo_env_enabled(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return (env.get("X_DEMO") or "").strip().lower() in DEMO_TRUTHY


def wants_demo(args: argparse.Namespace) -> bool:
    if getattr(args, "live", False):
        return False
    if getattr(args, "demo", False):
        return True
    return demo_env_enabled()


def resolve_demo_path(path: Path | None = None) -> Path:
    if path and path.is_file():
        return path
    if DEFAULT_DEMO_PATH.is_file():
        return DEFAULT_DEMO_PATH
    if FIXTURE_DEMO_PATH.is_file():
        return FIXTURE_DEMO_PATH
    raise XFeedError(
        "Demo fixture missing. Expected data/demo/x-search-recent.json "
        "or tests/fixtures/x-search-recent.json."
    )


def load_demo_payload(path: Path | None = None) -> dict[str, Any]:
    demo_path = resolve_demo_path(path)
    try:
        payload = json.loads(demo_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise XFeedError(f"Could not read demo fixture {demo_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise XFeedError(f"Demo fixture is not a JSON object: {demo_path}")
    if not isinstance(payload.get("data"), list) and not isinstance(payload.get("results"), list):
        raise XFeedError(f"Demo fixture needs data[] or results[]: {demo_path}")
    try:
        payload["_demoPath"] = str(demo_path.relative_to(PLUGIN_ROOT))
    except ValueError:
        payload["_demoPath"] = str(demo_path)
    return payload


def build_query(user_query: str | None) -> str:
    extra = (user_query or "").strip()
    if not extra:
        return DEFAULT_DISCOVERY_QUERY
    lowered = extra.lower()
    if any(token in lowered for token in ("x.ai", "grokbot", "grok bot", "url:")):
        return extra
    return f"({extra}) ({DEFAULT_DISCOVERY_QUERY})"


def _parse_json_body(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise XFeedError(f"X API returned non-JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise XFeedError("X API JSON was not an object")
    return payload


def _x_error_message(payload: dict[str, Any], status: int) -> str:
    bits: list[str] = []
    if payload.get("detail"):
        bits.append(str(payload["detail"]))
    for err in payload.get("errors") or []:
        if isinstance(err, dict):
            bits.append(str(err.get("message") or err.get("title") or err))
        else:
            bits.append(str(err))
    if payload.get("title") and payload["title"] not in " ".join(bits):
        bits.insert(0, str(payload["title"]))
    text = "; ".join(bits) if bits else raw_status_hint(status)
    return f"X API HTTP {status}: {text}"


def raw_status_hint(status: int) -> str:
    if status == 401:
        return "Bearer token rejected. Check X_BEARER_TOKEN."
    if status == 403:
        return (
            "Forbidden. This App may lack recent-search access "
            "(X API Basic or higher with search Posts)."
        )
    if status == 429:
        return "Rate limited. Wait and retry (recent search is quota-limited)."
    return "request failed"


def x_search_request(
    *,
    query: str,
    token: str,
    max_results: int = 25,
    since_id: str | None = None,
    next_token: str | None = None,
    urlopen: UrlOpen | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    opener = urlopen or urllib.request.urlopen
    max_results = max(10, min(100, int(max_results)))
    params: dict[str, str] = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "created_at,public_metrics,author_id,entities,lang",
        "expansions": "author_id",
        "user.fields": "username,name,profile_image_url",
    }
    if since_id:
        params["since_id"] = since_id
    if next_token:
        params["next_token"] = next_token
    url = X_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, "status", None) or getattr(resp, "code", 200)
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                payload = {"detail": body.decode("utf-8", errors="replace")[:300]}
        message = _x_error_message(payload if isinstance(payload, dict) else {}, exc.code)
        if exc.code in (401, 403):
            raise XAuthError(message) from exc
        raise XFeedError(message) from exc
    except urllib.error.URLError as exc:
        raise XFeedError(f"Failed to reach X API: {exc}") from exc
    if status >= 400:
        payload = _parse_json_body(raw) if raw else {}
        message = _x_error_message(payload, int(status))
        if status in (401, 403):
            raise XAuthError(message)
        raise XFeedError(message)
    return _parse_json_body(raw)


def collect_urls(tweet: dict[str, Any]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        url = url.rstrip(").,;\"'")
        if url and url not in seen:
            seen.add(url)
            found.append(url)

    for match in URL_RE.findall(tweet.get("text") or ""):
        add(match)
    for match in GROKBOT_URL_RE.findall(tweet.get("text") or ""):
        add(match)
    for match in GROKBOT_HREF_RE.finditer(tweet.get("text") or ""):
        add(f"grokbot://app/v1/bot-template?id={match.group(1)}")
    entities = tweet.get("entities") or {}
    for item in entities.get("urls") or []:
        if not isinstance(item, dict):
            continue
        for key in ("unwound_url", "expanded_url", "display_url", "url"):
            value = item.get(key)
            if value:
                if key == "display_url" and not str(value).startswith("http"):
                    add("https://" + str(value).lstrip("/"))
                else:
                    add(str(value))
    return found


def extract_bot_refs(urls: list[str], text: str) -> dict[str, list[str]]:
    marketplace_urls: list[str] = []
    add_hrefs: list[str] = []
    slugs: list[str] = []
    template_ids: list[str] = []
    share_urls: list[str] = []
    blob = " ".join(urls) + " " + (text or "")

    def add_unique(bucket: list[str], value: str) -> None:
        value = value.rstrip(").,;\"'")
        if value and value not in bucket:
            bucket.append(value)

    for match in MARKETPLACE_BOT_RE.finditer(blob):
        slug = match.group(1)
        page = f"https://x.ai/bot/marketplace/bots/{slug}"
        add_unique(marketplace_urls, page)
        add_unique(slugs, slug)
    for url in urls:
        lowered = url.lower()
        if "x.ai/bot/marketplace" in lowered:
            cleaned = url.split("?")[0].rstrip("/")
            add_unique(marketplace_urls, cleaned)
        if "grokbot://" in lowered:
            add_unique(add_hrefs, url.split()[0])
        if SHARE_TEMPLATE_RE.search(url) or "bot-template" in lowered:
            add_unique(share_urls, url)
    for match in MARKETPLACE_LISTING_RE.finditer(blob):
        add_unique(marketplace_urls, "https://x.ai/bot/marketplace")
    for match in GROKBOT_HREF_RE.finditer(blob):
        href = f"grokbot://app/v1/bot-template?id={match.group(1)}"
        add_unique(add_hrefs, href)
        add_unique(template_ids, match.group(1))
    for match in TEMPLATE_ID_QUERY_RE.finditer(blob):
        add_unique(template_ids, match.group(1))
    for match in SHARE_TEMPLATE_RE.finditer(blob):
        add_unique(share_urls, match.group(0).rstrip(").,;\"'"))
    return {
        "marketplaceUrls": marketplace_urls,
        "addHrefs": add_hrefs,
        "botSlugs": slugs,
        "templateIds": template_ids,
        "shareUrls": share_urls,
    }


def _users_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    users = {}
    for user in ((payload.get("includes") or {}).get("users") or []):
        if isinstance(user, dict) and user.get("id"):
            users[str(user["id"])] = user
    return users


def normalize_post(tweet: dict[str, Any], users: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tweet_id = str(tweet.get("id") or "")
    author_id = str(tweet.get("author_id") or "")
    user = users.get(author_id) or {}
    username = str(user.get("username") or "")
    text = str(tweet.get("text") or "")
    urls = collect_urls(tweet)
    refs = extract_bot_refs(urls, text)
    metrics = tweet.get("public_metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    post_url = f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/web/status/{tweet_id}"
    return {
        "id": tweet_id,
        "postUrl": post_url,
        "createdAt": tweet.get("created_at"),
        "lang": tweet.get("lang"),
        "text": text,
        "author": {
            "id": author_id,
            "username": username,
            "name": str(user.get("name") or ""),
        },
        "metrics": {
            "likeCount": int(metrics.get("like_count") or 0),
            "retweetCount": int(metrics.get("retweet_count") or 0),
            "replyCount": int(metrics.get("reply_count") or 0),
            "quoteCount": int(metrics.get("quote_count") or 0),
            "bookmarkCount": int(metrics.get("bookmark_count") or 0) if metrics.get("bookmark_count") is not None else None,
            "impressionCount": int(metrics.get("impression_count") or 0) if metrics.get("impression_count") is not None else None,
        },
        "urls": urls,
        **refs,
        "matchedBots": [],
        "feed": "x",
        "source": "x",
    }


def join_catalog(posts: list[dict[str, Any]], catalog_path: Path) -> list[dict[str, Any]]:
    import catalog as catalog_mod

    try:
        document = catalog_mod.load_catalog(catalog_path)
    except catalog_mod.CatalogError:
        return posts
    bots = document.get("bots") or []
    by_slug = {str(b.get("id") or "").lower(): b for b in bots if b.get("id")}
    by_template: dict[str, Any] = {}
    for bot in bots:
        match = GROKBOT_HREF_RE.search(str(bot.get("addHref") or ""))
        if match:
            by_template[match.group(1)] = bot
    for post in posts:
        matched: list[dict[str, Any]] = []
        seen: set[str] = set()
        for slug in post.get("botSlugs") or []:
            bot = by_slug.get(str(slug).lower())
            if bot and bot["id"] not in seen:
                seen.add(bot["id"])
                matched.append(catalog_mod.public_card(bot))
        for template_id in post.get("templateIds") or []:
            bot = by_template.get(template_id)
            if bot and bot["id"] not in seen:
                seen.add(bot["id"])
                matched.append(catalog_mod.public_card(bot))
        post["matchedBots"] = matched
        if matched and not post.get("addHrefs"):
            post["addHrefs"] = [c["addHref"] for c in matched if c.get("addHref")]
        if matched and not post.get("marketplaceUrls"):
            post["marketplaceUrls"] = [c["marketplaceUrl"] for c in matched if c.get("marketplaceUrl")]
    return posts


def engagement_score(post: dict[str, Any]) -> int:
    metrics = post.get("metrics") or {}
    return (
        int(metrics.get("likeCount") or 0)
        + 2 * int(metrics.get("retweetCount") or 0)
        + 2 * int(metrics.get("quoteCount") or 0)
        + int(metrics.get("replyCount") or 0)
    )


def sort_posts(posts: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "engagement":
        return sorted(posts, key=engagement_score, reverse=True)
    return posts


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_checkpoint(path: Path, *, since_id: str, query: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sinceId": since_id,
        "query": query,
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def search_posts(
    *,
    query: str,
    token: str,
    max_results: int = 25,
    since_id: str | None = None,
    urlopen: UrlOpen | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    opener = urlopen or urllib.request.urlopen
    try:
        payload = x_search_request(
            query=query,
            token=token,
            max_results=max_results,
            since_id=since_id,
            urlopen=opener,
        )
    except XFeedError as exc:
        # since_id outside the 7-day window → retry once without it.
        if since_id and "since_id" in str(exc).lower():
            payload = x_search_request(
                query=query,
                token=token,
                max_results=max_results,
                urlopen=opener,
            )
            payload["_sinceIdIgnored"] = True
        else:
            raise
    users = _users_by_id(payload)
    posts = [normalize_post(t, users) for t in payload.get("data") or [] if isinstance(t, dict)]
    meta = payload.get("meta") or {}
    if payload.get("_sinceIdIgnored"):
        meta = dict(meta)
        meta["sinceIdIgnored"] = True
    return posts, meta if isinstance(meta, dict) else {}


def posts_from_demo_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Turn a checked-in X search JSON (or a results envelope) into posts."""
    if isinstance(payload.get("results"), list) and payload.get("data") is None:
        posts = []
        for item in payload["results"]:
            if not isinstance(item, dict):
                continue
            post = dict(item)
            post.setdefault("feed", "x")
            post.setdefault("source", "x")
            post.setdefault("matchedBots", [])
            posts.append(post)
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        meta = dict(meta)
        meta["demo"] = True
        if payload.get("_demoPath"):
            meta["fixture"] = payload["_demoPath"]
        return posts, meta
    users = _users_by_id(payload)
    posts = [normalize_post(t, users) for t in payload.get("data") or [] if isinstance(t, dict)]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta = dict(meta)
    meta["demo"] = True
    if payload.get("_demoPath"):
        meta["fixture"] = payload["_demoPath"]
    return posts, meta


def filter_demo_posts(posts: list[dict[str, Any]], user_query: str | None) -> list[dict[str, Any]]:
    extra = (user_query or "").strip()
    if not extra:
        return posts
    lowered = extra.lower()
    if any(token in lowered for token in ("x.ai", "grokbot", "grok bot", "url:", " or ")):
        return posts
    return [p for p in posts if extra.lower() in (p.get("text") or "").lower()]


def feed_envelope(
    *,
    posts: list[dict[str, Any]],
    query: str,
    meta: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = extra or {}
    payload = {
        "source": "x-demo-fixture" if extra.get("demo") else "x-api-v2-recent-search",
        "feed": "x",
        "mode": extra.get("mode") or "x-feed",
        "demo": bool(extra.get("demo")),
        "live": bool(extra.get("live")),
        "query": query,
        "sort": extra.get("sort"),
        "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resultCount": len(posts),
        "meta": {
            "newestId": meta.get("newest_id") or meta.get("newestId"),
            "oldestId": meta.get("oldest_id") or meta.get("oldestId"),
            "resultCount": meta.get("result_count") or meta.get("resultCount"),
            "sinceIdIgnored": bool(meta.get("sinceIdIgnored")),
            "fixture": meta.get("fixture"),
        },
        "install": {
            "method": "grokbot-deeplink",
            "note": (
                "Install is only via addHref grokbot:// or the marketplace URL. "
                "X posts are a discovery feed — never POST an install API."
            ),
        },
        "results": posts,
    }
    skip = {"demo", "live", "mode", "sort"}
    if extra:
        for key, value in extra.items():
            if key not in skip:
                payload[key] = value
    return payload


def print_text_feed(payload: dict[str, Any]) -> None:
    mode = "demo" if payload.get("demo") else "live"
    print(f"feed: x ({mode})")
    print(f"Source: {payload.get('source')}  query={payload.get('query')}")
    print(
        f"Results: {payload.get('resultCount')}  sort={payload.get('sort') or '—'}  "
        f"(fetched {payload.get('fetchedAt')})"
    )
    if payload.get("demo"):
        print("Offline demo fixture — not live X. Set X_BEARER_TOKEN and pass --live for real search.")
    if payload.get("checkpoint"):
        print(f"Checkpoint: {payload['checkpoint']}")
    print("Install is a grokbot:// / marketplace URL — not an API.")
    print()
    for post in payload.get("results") or []:
        author = post.get("author") or {}
        handle = f"@{author.get('username')}" if author.get("username") else author.get("name") or "unknown"
        metrics = post.get("metrics") or {}
        likes = metrics.get("likeCount") or 0
        rts = metrics.get("retweetCount") or 0
        snippet = (post.get("text") or "").replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:219].rstrip() + "…"
        print(f"- {handle}  {post.get('postUrl')}")
        print(f"  {snippet}")
        print(f"  likes {likes}  retweets {rts}  {post.get('createdAt')}")
        for href in post.get("addHrefs") or []:
            print(f"  addHref: {href}")
        for url in post.get("marketplaceUrls") or []:
            print(f"  marketplace: {url}")
        for bot in post.get("matchedBots") or []:
            print(
                f"  matched [marketplace]: {bot.get('name')} — {bot.get('creator')}  "
                f"{bot.get('marketplaceUrl')}"
            )
        if not post.get("matchedBots"):
            print("  matched: (not in catalog snapshot — raw share card)")
        print()


def emit(payload: dict[str, Any], fmt: str) -> None:
    if fmt == "text":
        print_text_feed(payload)
        return
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _run_search(args: argparse.Namespace, *, monitor: bool) -> int:
    live = bool(getattr(args, "live", False))
    demo = wants_demo(args)
    token: str | None = None
    try:
        token = resolve_bearer_token()
    except XAuthError as exc:
        if live:
            json.dump(auth_error_payload(str(exc), demo_fallback=False), sys.stderr, indent=2)
            sys.stderr.write("\n")
            return 3
        demo = True
        json.dump(auth_error_payload(str(exc), demo_fallback=True), sys.stderr, indent=2)
        sys.stderr.write("\n")

    query = build_query(getattr(args, "query", None))
    checkpoint_path = Path(getattr(args, "checkpoint", None) or DEFAULT_CHECKPOINT_PATH)
    sort = getattr(args, "sort", None) or ("recent" if monitor else "engagement")

    if demo:
        try:
            raw = load_demo_payload()
            posts, meta = posts_from_demo_payload(raw)
            posts = filter_demo_posts(posts, getattr(args, "query", None))
        except XFeedError as exc:
            json.dump({"error": str(exc), "setup": {"hint": SETUP_HINT}}, sys.stderr, indent=2)
            sys.stderr.write("\n")
            return 2
        posts = join_catalog(posts, Path(args.catalog))
        posts = sort_posts(posts, sort)
        extra: dict[str, Any] = {
            "sinceIdUsed": None,
            "demo": True,
            "live": False,
            "mode": "x-feed-demo",
            "sort": sort,
        }
        emit(feed_envelope(posts=posts, query=query, meta=meta, extra=extra), args.format)
        return 0

    assert token is not None
    since_id = None
    if monitor and not getattr(args, "reset", False):
        since_id = getattr(args, "since_id", None) or load_checkpoint(checkpoint_path).get("sinceId")
    elif getattr(args, "since_id", None):
        since_id = args.since_id
    try:
        posts, meta = search_posts(
            query=query,
            token=token,
            max_results=getattr(args, "max_results", 25),
            since_id=since_id,
        )
    except XAuthError as exc:
        json.dump(auth_error_payload(str(exc), demo_fallback=False), sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 3
    except XFeedError as exc:
        json.dump({"error": str(exc), "setup": {"hint": SETUP_HINT}}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2
    posts = join_catalog(posts, Path(args.catalog))
    posts = sort_posts(posts, sort)
    extra = {
        "sinceIdUsed": since_id,
        "demo": False,
        "live": True,
        "mode": "x-feed",
        "sort": sort,
    }
    newest = (meta.get("newest_id") or meta.get("newestId") or (posts[0]["id"] if posts else None))
    if monitor or getattr(args, "save_checkpoint", False):
        if newest:
            save_checkpoint(checkpoint_path, since_id=str(newest), query=query)
            extra["checkpoint"] = str(checkpoint_path)
            extra["checkpointSinceId"] = str(newest)
        else:
            extra["checkpoint"] = str(checkpoint_path)
            extra["checkpointUnchanged"] = True
    if getattr(args, "reset", False) and monitor and not posts and not newest:
        extra["checkpointReset"] = True
    emit(feed_envelope(posts=posts, query=query, meta=meta, extra=extra), args.format)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    return _run_search(args, monitor=False)


def cmd_viral(args: argparse.Namespace) -> int:
    args.sort = "engagement"
    return _run_search(args, monitor=False)


def cmd_monitor(args: argparse.Namespace) -> int:
    return _run_search(args, monitor=True)


def add_x_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Optional extra keywords (ANDed with the marketplace discovery query)",
    )
    parser.add_argument("--max-results", type=int, default=25, dest="max_results")
    parser.add_argument("--since-id", dest="since_id", help="Only posts newer than this tweet id")
    parser.add_argument(
        "--checkpoint",
        default=str(DEFAULT_CHECKPOINT_PATH),
        help="Checkpoint JSON for x-monitor (default: data/x-checkpoint.json)",
    )
    parser.add_argument(
        "--sort",
        choices=("recent", "engagement"),
        default=None,
        help="recent = API order; engagement = likes/reposts (default: engagement for search, recent for monitor)",
    )
    parser.add_argument(
        "--save-checkpoint",
        action="store_true",
        help="Write data/x-checkpoint.json from this search (x-monitor always writes)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore existing checkpoint (monitor starts from latest window)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use checked-in demo fixture (no network, no token required)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force live X API. Fails with setup instructions if no Bearer token",
    )


def build_parser() -> argparse.ArgumentParser:
    import catalog as catalog_mod

    shared = catalog_mod._shared_cli_flags()
    parser = argparse.ArgumentParser(
        description="Discover Grok Bot template shares on X (read-only recent search).",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_search = sub.add_parser("search", parents=[shared], help="Search recent X posts")
    add_x_arguments(p_search)
    p_search.set_defaults(func=cmd_search, sort="engagement")
    p_viral = sub.add_parser(
        "viral",
        aliases=["trending"],
        parents=[shared],
        help="Same search ranked by engagement (viral / trending)",
    )
    add_x_arguments(p_viral)
    p_viral.set_defaults(func=cmd_viral, sort="engagement")
    p_mon = sub.add_parser("monitor", parents=[shared], help="Fetch posts newer than the checkpoint")
    add_x_arguments(p_mon)
    p_mon.set_defaults(func=cmd_monitor, sort="recent")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.sort is None:
        args.sort = "recent" if args.command == "monitor" else "engagement"
    try:
        return int(args.func(args))
    except XAuthError as exc:
        json.dump(auth_error_payload(str(exc)), sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 3
    except XFeedError as exc:
        json.dump({"error": str(exc)}, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
