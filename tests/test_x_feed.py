import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import catalog  # noqa: E402
import x_feed  # noqa: E402


class FakeHTTPResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status
        self.code = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ExtractTests(unittest.TestCase):
    def test_extracts_marketplace_and_grokbot_links(self):
        tweet = {
            "text": "try this grokbot://app/v1/bot-template?id=abc_12",
            "entities": {
                "urls": [
                    {
                        "expanded_url": "https://x.ai/bot/marketplace/bots/researchy",
                        "url": "https://t.co/x",
                    }
                ]
            },
        }
        urls = x_feed.collect_urls(tweet)
        refs = x_feed.extract_bot_refs(urls, tweet["text"])
        self.assertIn("https://x.ai/bot/marketplace/bots/researchy", refs["marketplaceUrls"])
        self.assertEqual(refs["botSlugs"], ["researchy"])
        self.assertEqual(refs["templateIds"], ["abc_12"])
        self.assertTrue(refs["addHrefs"][0].startswith("grokbot://"))

    def test_build_query_ands_plain_keywords(self):
        q = x_feed.build_query("researchy")
        self.assertIn("researchy", q)
        self.assertIn("x.ai/bot/marketplace", q)
        self.assertEqual(x_feed.build_query('url:x.ai/bot'), "url:x.ai/bot")


class AuthTests(unittest.TestCase):
    def test_missing_token_is_explicit(self):
        with self.assertRaises(x_feed.XAuthError) as ctx:
            x_feed.resolve_bearer_token({})
        self.assertIn("X_BEARER_TOKEN", str(ctx.exception))

    def test_aliases_and_dotenv_do_not_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text('X_BEARER_TOKEN="fromfile"\nTWITTER_BEARER_TOKEN=alias\n', encoding="utf-8")
            env: dict[str, str] = {}
            x_feed.load_env_file(path, env)
            self.assertEqual(env["X_BEARER_TOKEN"], "fromfile")
            env2 = {"X_BEARER_TOKEN": "existing"}
            x_feed.load_env_file(path, env2)
            self.assertEqual(env2["X_BEARER_TOKEN"], "existing")
            self.assertEqual(x_feed.resolve_bearer_token({"TWITTER_BEARER_TOKEN": "tw"}), "tw")

    def test_cli_without_token_exits_3(self):
        env = {k: v for k, v in os.environ.items() if k not in x_feed.TOKEN_ENV_NAMES}
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            x_feed, "DEFAULT_ENV_PATH", Path("/tmp/grok-bot-marketplace-no-env")
        ), mock.patch("sys.stderr", err):
            code = catalog.main(["x-search", "--max-results", "10"])
        self.assertEqual(code, 3)
        payload = json.loads(err.getvalue())
        self.assertEqual(payload["setup"]["env"], "X_BEARER_TOKEN")
        self.assertTrue(payload["marketplaceStillWorks"])


class SearchMockTests(unittest.TestCase):
    def setUp(self):
        self.fixture = (ROOT / "tests" / "fixtures" / "x-search-recent.json").read_bytes()
        self.catalog = ROOT / "data" / "catalog.json"

    def _open(self, req, timeout=None):
        self.last_url = getattr(req, "full_url", None) or req.get_full_url()
        self.last_headers = dict(req.header_items()) if hasattr(req, "header_items") else dict(req.headers)
        return FakeHTTPResponse(self.fixture)

    def test_search_joins_catalog_and_keeps_raw_share(self):
        posts, meta = x_feed.search_posts(
            query="test",
            token="tok",
            urlopen=self._open,
        )
        self.assertEqual(meta["newest_id"], "1987654321098765432")
        posts = x_feed.join_catalog(posts, self.catalog)
        researchy = next(p for p in posts if "researchy" in (p.get("botSlugs") or []))
        self.assertEqual(researchy["author"]["username"], "farzyness")
        self.assertTrue(researchy["postUrl"].endswith("/1987654321098765432"))
        self.assertGreaterEqual(len(researchy["matchedBots"]), 1)
        self.assertEqual(researchy["matchedBots"][0]["id"], "researchy")
        self.assertTrue(researchy["matchedBots"][0]["addHref"].startswith("grokbot://"))
        raw = next(p for p in posts if "unlisted-demo" in (p.get("botSlugs") or []))
        self.assertEqual(raw["matchedBots"], [])
        self.assertTrue(raw["marketplaceUrls"])

    def test_engagement_sort(self):
        posts, _ = x_feed.search_posts(query="test", token="tok", urlopen=self._open)
        ranked = x_feed.sort_posts(posts, "engagement")
        self.assertEqual(ranked[0]["id"], "1987654321098765432")

    def test_monitor_sends_since_id_and_writes_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            ck = Path(tmp) / "x-checkpoint.json"
            env = {"X_BEARER_TOKEN": "tok"}
            out = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=False), mock.patch(
                "x_feed.urllib.request.urlopen", self._open
            ), mock.patch("sys.stdout", out):
                # First call: no checkpoint
                code = x_feed.main(
                    [
                        "--catalog",
                        str(self.catalog),
                        "monitor",
                        "--checkpoint",
                        str(ck),
                        "--max-results",
                        "10",
                    ]
                )
            self.assertEqual(code, 0)
            saved = json.loads(ck.read_text(encoding="utf-8"))
            self.assertEqual(saved["sinceId"], "1987654321098765432")
            with mock.patch.dict(os.environ, env, clear=False), mock.patch(
                "x_feed.urllib.request.urlopen", self._open
            ), mock.patch("sys.stdout", io.StringIO()):
                x_feed.main(
                    [
                        "--catalog",
                        str(self.catalog),
                        "monitor",
                        "--checkpoint",
                        str(ck),
                    ]
                )
            self.assertIn("since_id=1987654321098765432", self.last_url)

    def test_http_401_is_auth_error(self):
        def boom(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url if hasattr(req, "full_url") else "https://api.x.com/2/tweets/search/recent",
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(json.dumps({"title": "Unauthorized", "detail": "bad token"}).encode()),
            )

        with self.assertRaises(x_feed.XAuthError) as ctx:
            x_feed.x_search_request(query="q", token="bad", urlopen=boom)
        self.assertIn("401", str(ctx.exception))


class CatalogHardenTests(unittest.TestCase):
    def test_http_error_message_includes_status(self):
        def boom(req, timeout=None):
            raise urllib.error.HTTPError(
                "https://x.ai/bot/marketplace",
                403,
                "Forbidden",
                hdrs=None,
                fp=io.BytesIO(b"blocked"),
            )

        with mock.patch("catalog.urllib.request.urlopen", boom):
            with self.assertRaises(catalog.CatalogError) as ctx:
                catalog.fetch_url("https://x.ai/bot/marketplace")
        self.assertIn("HTTP 403", str(ctx.exception))

    def test_parse_templates_fallback_without_templates_key(self):
        payload = json.dumps(
            {
                "id": "fallback-bot",
                "name": "Fallback",
                "creatorName": "Ada",
                "addHref": "grokbot://app/v1/bot-template?id=fb1",
            },
            separators=(",", ":"),
        )
        html = (
            "<html><script>self.__next_f.push([1,"
            + json.dumps("row:" + payload)
            + "])</script></html>"
        )
        templates = catalog.parse_templates(html)
        self.assertEqual(templates[0]["id"], "fallback-bot")
        self.assertTrue(templates[0]["addHref"].startswith("grokbot://"))


if __name__ == "__main__":
    unittest.main()
