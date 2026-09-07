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
import feed_client  # noqa: E402


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


def sample_feed() -> dict:
    return {
        "marketplace": {
            "source": "https://grokbots.store/feed.json",
            "fetchedAt": "2026-09-07T00:00:00Z",
            "botCount": 1,
            "install": {
                "method": "grokbot-deeplink",
                "note": "open grokbot://",
            },
            "bots": [
                {
                    "id": "seo-desk",
                    "name": "SEO Desk",
                    "creatorName": "Ada Lovelace",
                    "handle": "ada",
                    "description": "Turns keywords into briefs.",
                    "summary": "Turns keywords into briefs.",
                    "categories": ["Marketing"],
                    "installCount": 12,
                    "addHref": "grokbot://app/v1/bot-template?id=seo123",
                    "marketplaceUrl": "https://x.ai/bot/marketplace/bots/seo-desk",
                }
            ],
        },
        "xViral": {
            "feed": "x",
            "source": "hosted-feed",
            "results": [
                {
                    "id": "1",
                    "text": "try Researchy grokbot://app/v1/bot-template?id=res",
                    "feed": "x",
                    "addHrefs": ["grokbot://app/v1/bot-template?id=res"],
                    "matchedBots": [],
                    "metrics": {"likeCount": 9, "retweetCount": 2, "replyCount": 0, "quoteCount": 0},
                    "author": {"username": "tester"},
                    "postUrl": "https://x.com/tester/status/1",
                }
            ],
        },
        "fetchedAt": "2026-09-07T00:00:00Z",
        "sources": {"marketplace": "x.ai", "x": "hosted"},
    }


class FeedClientTests(unittest.TestCase):
    def test_validate_and_sections(self):
        feed = feed_client.validate_feed(sample_feed())
        market = feed_client.marketplace_document(feed)
        self.assertEqual(market["bots"][0]["id"], "seo-desk")
        xv = feed_client.x_viral_envelope(feed)
        self.assertEqual(xv["resultCount"], 1)
        self.assertEqual(xv["results"][0]["feed"], "x")

    def test_list_wrap_is_valid(self):
        feed = {
            "marketplace": sample_feed()["marketplace"]["bots"],
            "xViral": [],
            "fetchedAt": "2026-09-07T00:00:00Z",
            "sources": {},
        }
        document = feed_client.marketplace_document(feed_client.validate_feed(feed))
        self.assertEqual(document["botCount"], 1)
        self.assertTrue(document["bots"][0]["addHref"].startswith("grokbot://"))

    def test_fetch_hosted_feed_mocked(self):
        payload = json.dumps(sample_feed()).encode()

        def opener(req, timeout=None):
            self.assertIn("grokbots.store", req.get_full_url())
            return FakeHTTPResponse(payload)

        feed = feed_client.fetch_hosted_feed(
            "https://grokbots.store/feed.json", urlopen=opener
        )
        self.assertEqual(feed["sources"]["dataSource"], "hosted")
        self.assertEqual(feed_client.marketplace_document(feed)["botCount"], 1)

    def test_load_feed_falls_back_to_snapshot(self):
        def boom(req, timeout=None):
            raise urllib.error.URLError("offline")

        feed = feed_client.load_feed(offline=False, urlopen=boom)
        self.assertIn(feed["sources"]["dataSource"], ("snapshot-fallback", "snapshot", "catalog-snapshot"))
        market = feed_client.marketplace_document(feed)
        self.assertGreaterEqual(market["botCount"], 1)
        self.assertTrue(market["bots"][0]["addHref"].startswith("grokbot://"))

    def test_offline_skips_http(self):
        def boom(*_a, **_k):
            raise AssertionError("offline must not HTTP")

        feed = feed_client.load_feed(offline=True, urlopen=boom)
        self.assertEqual(feed["sources"]["dataSource"], "snapshot")

    def test_cli_list_uses_hosted_feed(self):
        payload = json.dumps(sample_feed()).encode()

        def opener(req, timeout=None):
            return FakeHTTPResponse(payload)

        out = io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "GROKBOTS_OFFLINE"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "feed_client.urllib.request.urlopen", opener
        ), mock.patch("sys.stdout", out):
            code = catalog.main(["list", "--limit", "5"])
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["feed"], "marketplace")
        self.assertEqual(body["dataSource"], "hosted")
        self.assertEqual(body["results"][0]["id"], "seo-desk")
        self.assertTrue(body["results"][0]["addHref"].startswith("grokbot://"))

    def test_cli_search_offline_uses_catalog_flag(self):
        snapshot = ROOT / "data" / "catalog.json"
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = catalog.main(
                ["--catalog", str(snapshot), "--offline", "search", "outbound", "--limit", "2"]
            )
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["dataSource"], "snapshot")
        self.assertEqual(body["feed"], "marketplace")

    def test_cli_offline_after_subcommand(self):
        snapshot = ROOT / "data" / "catalog.json"
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = catalog.main(
                ["search", "--offline", "--catalog", str(snapshot), "outbound", "--limit", "2"]
            )
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["dataSource"], "snapshot")


class HostedXFeedTests(unittest.TestCase):
    def test_x_viral_reads_hosted_feed_without_token(self):
        payload = json.dumps(sample_feed()).encode()

        def opener(req, timeout=None):
            return FakeHTTPResponse(payload)

        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN", "X_API_BEARER_TOKEN", "X_DEMO", "GROKBOTS_OFFLINE")
        }
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "feed_client.urllib.request.urlopen", opener
        ), mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = catalog.main(["x-viral", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue().strip(), "")
        body = json.loads(out.getvalue())
        self.assertEqual(body["feed"], "x")
        self.assertFalse(body["live"])
        self.assertEqual(body["dataSource"], "hosted")
        self.assertGreaterEqual(body["resultCount"], 1)
        self.assertTrue(any("grokbot://" in (p.get("text") or "") for p in body["results"]))

    def test_x_search_feed_http_error_falls_back_without_bearer_nag(self):
        def boom(req, timeout=None):
            raise urllib.error.URLError("offline")

        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN", "X_API_BEARER_TOKEN", "X_DEMO", "GROKBOTS_OFFLINE")
        }
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch(
            "feed_client.urllib.request.urlopen", boom
        ), mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = catalog.main(["x-search", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertNotIn("Create a Project", err.getvalue())
        body = json.loads(out.getvalue())
        self.assertEqual(body["feed"], "x")
        self.assertGreaterEqual(body["resultCount"], 1)


class OpsRefreshTests(unittest.TestCase):
    def test_from_snapshot_demo_x_writes_schema(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "refresh_feed", ROOT / "ops" / "refresh_feed.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "feed.json"
            err = io.StringIO()
            stdout = io.StringIO()
            with mock.patch("sys.stderr", err), mock.patch("sys.stdout", stdout):
                code = mod.main(["--from-snapshot", "--demo-x", "--out", str(out)])
            self.assertEqual(code, 0, err.getvalue())
            feed = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("marketplace", feed)
            self.assertIn("xViral", feed)
            self.assertIn("fetchedAt", feed)
            self.assertIn("sources", feed)
            self.assertGreaterEqual(feed["marketplace"]["botCount"], 1)
            self.assertGreaterEqual(feed["xViral"]["resultCount"], 1)
            self.assertTrue(feed["marketplace"]["bots"][0]["addHref"].startswith("grokbot://"))


if __name__ == "__main__":
    unittest.main()
