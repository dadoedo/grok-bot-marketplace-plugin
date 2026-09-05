import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import catalog  # noqa: E402


def flight_html(payload_text: str) -> str:
    encoded = json.dumps(payload_text)
    return (
        "<!DOCTYPE html><html><body>"
        "<script>self.__next_f=self.__next_f||[]</script>"
        f"<script>self.__next_f.push([1,{encoded}])</script>"
        "</body></html>"
    )


SAMPLE_BOTS = [
    {
        "id": "seo-desk",
        "name": "SEO Desk",
        "creatorName": "Ada Lovelace",
        "handle": "ada",
        "description": "Turns keywords into briefs.",
        "summary": "Turns keywords into briefs.",
        "categories": ["Marketing"],
        "installCount": 12,
        "color": "blue",
        "shape": "circle",
        "addHref": "grokbot://app/v1/bot-template?id=seo123",
        "imageUrl": "https://grok-bot-marketplace-public-assets.s3.amazonaws.com/img/creators/ada.png",
        "instructions": "",
    },
    {
        "id": "researchy",
        "name": "Researchy",
        "creatorName": "Farzad",
        "handle": "farzad",
        "description": "A research and fact-check desk.",
        "summary": "A research and fact-check desk.",
        "categories": ["Engineering", "From Grok Bot Team"],
        "installCount": 0,
        "color": "red",
        "shape": "teardrop",
        "addHref": "grokbot://app/v1/bot-template?id=res456",
        "imageUrl": "https://example.com/farzad.png",
        "instructions": "Always cite sources.",
        "memories": [{"id": "m1", "name": "memory 1", "description": "Cite the web."}],
        "skills": [{"id": "s1", "name": "Research", "description": "Search then cite."}],
        "routines": [],
        "integrations": [],
    },
    {
        "id": "eng-ops",
        "name": "Eng Ops",
        "creatorName": "Casey",
        "handle": "casey",
        "description": "Keeps engineering ops tidy.",
        "summary": "Keeps engineering ops tidy.",
        "categories": ["Engineering Ops"],
        "installCount": 3,
        "color": "green",
        "shape": "circle",
        "addHref": "grokbot://app/v1/bot-template?id=ops789",
        "imageUrl": "https://example.com/casey.png",
        "instructions": "",
    },
]


class CatalogParseTests(unittest.TestCase):
    def test_parse_templates_from_flight_payload(self):
        compact = json.dumps(
            {"featured": {"bots": []}, "templates": SAMPLE_BOTS},
            separators=(",", ":"),
        )
        pretty = json.dumps({"featured": {"bots": []}, "templates": SAMPLE_BOTS})
        for payload in (compact, pretty):
            templates = catalog.parse_templates(flight_html(payload))
            self.assertEqual(len(templates), 3)
            self.assertEqual(templates[0]["id"], "seo-desk")
            self.assertTrue(templates[0]["addHref"].startswith("grokbot://"))

    def test_parse_bot_detail(self):
        html = flight_html(json.dumps(SAMPLE_BOTS[1]))
        bot = catalog.parse_bot_detail(html, "researchy")
        self.assertEqual(bot["id"], "researchy")
        self.assertEqual(bot["instructions"], "Always cite sources.")

    def test_missing_payload_errors(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.parse_templates("<html><body>no catalog</body></html>")

    def test_parse_real_next_f_fixture_offline(self):
        fixture = ROOT / "tests" / "fixtures" / "marketplace-next-f.html"
        html = fixture.read_text(encoding="utf-8")
        templates = catalog.parse_templates(html)
        self.assertGreaterEqual(len(templates), 1)
        hrefs = [t.get("addHref") or "" for t in templates]
        self.assertTrue(any(h.startswith("grokbot://") for h in hrefs))
        self.assertIn("self.__next_f.push", html)
        self.assertIn("templates", html)
        self.assertIn("grokbot://", html)


class CatalogQueryTests(unittest.TestCase):
    def setUp(self):
        self.bots = [catalog.normalize_bot(b) for b in SAMPLE_BOTS]

    def test_normalize_marketplace_url_and_fields(self):
        bot = self.bots[0]
        self.assertEqual(bot["marketplaceUrl"], "https://x.ai/bot/marketplace/bots/seo-desk")
        self.assertEqual(bot["addHref"], "grokbot://app/v1/bot-template?id=seo123")
        card = catalog.public_card(bot)
        self.assertEqual(card["creator"], "Ada Lovelace")
        self.assertEqual(card["installCount"], 12)
        for field in catalog.CARD_FIELDS:
            self.assertIn(field, card)
        self.assertIsInstance(card["name"], str)
        self.assertIsInstance(card["creator"], str)
        self.assertIsInstance(card["description"], str)
        self.assertIsInstance(card["addHref"], str)
        self.assertIsInstance(card["marketplaceUrl"], str)
        self.assertIn("marketplaceUrl", card)
        self.assertIn("addHref", card)

    def test_search_keyword_and_category(self):
        hits = catalog.filter_bots(self.bots, query="keyword briefs")
        self.assertEqual([b["id"] for b in hits], ["seo-desk"])
        hits = catalog.filter_bots(self.bots, category="engineering")
        self.assertEqual([b["id"] for b in hits], ["researchy"])
        hits = catalog.filter_bots(self.bots, category="ops")
        self.assertEqual([b["id"] for b in hits], ["eng-ops"])

    def test_compare_resolves_name_and_id(self):
        found, missing = catalog.find_bots(self.bots, ["SEO Desk", "researchy"])
        self.assertEqual([b["id"] for b in found], ["seo-desk", "researchy"])
        self.assertEqual(missing, [])

    def test_unknown_id_is_missing(self):
        found, missing = catalog.find_bots(self.bots, ["no-such-bot"])
        self.assertEqual(found, [])
        self.assertEqual(missing, ["no-such-bot"])

    def test_snapshot_roundtrip(self):
        document = catalog.build_catalog_document(SAMPLE_BOTS, fetched_at="2026-09-05T00:00:00Z")
        self.assertEqual(document["botCount"], 3)
        self.assertEqual(document["install"]["method"], "grokbot-deeplink")
        self.assertTrue(any(c["name"] == "Marketing" for c in document["categories"]))
        cards = [catalog.public_card(b) for b in document["bots"]]
        self.assertTrue(all(c["addHref"].startswith("grokbot://") for c in cards))
        for card in cards:
            for field in (
                "name",
                "creator",
                "description",
                "addHref",
                "marketplaceUrl",
            ):
                self.assertIn(field, card)
                self.assertIsInstance(card[field], str)
                self.assertTrue(card[field])


class CatalogCliTests(unittest.TestCase):
    def test_checked_in_snapshot_has_required_fields(self):
        snapshot = ROOT / "data" / "catalog.json"
        if not snapshot.is_file():
            self.skipTest("checked-in catalog snapshot missing")
        document = json.loads(snapshot.read_text(encoding="utf-8"))
        self.assertGreaterEqual(document["botCount"], 1)
        self.assertEqual(len(document["bots"]), document["botCount"])
        self.assertEqual(document["install"]["method"], "grokbot-deeplink")
        for bot in document["bots"]:
            self.assertTrue(bot["id"])
            self.assertTrue(bot["name"])
            self.assertTrue(bot["addHref"].startswith("grokbot://"))
            self.assertEqual(
                bot["marketplaceUrl"],
                f"https://x.ai/bot/marketplace/bots/{bot['id']}",
            )

    def test_search_cli_json(self):
        snapshot = ROOT / "data" / "catalog.json"
        if not snapshot.is_file():
            self.skipTest("checked-in catalog snapshot missing")
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = catalog.main(["--catalog", str(snapshot), "search", "seo", "--limit", "3"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("results", payload)
        self.assertEqual(payload["install"]["method"], "grokbot-deeplink")
        for bot in payload["results"]:
            self.assertTrue(bot["addHref"].startswith("grokbot://"))
            self.assertTrue(bot["marketplaceUrl"].startswith("https://x.ai/bot/marketplace/bots/"))
            for field in ("name", "creator", "description", "addHref", "marketplaceUrl"):
                self.assertIn(field, bot)
                self.assertTrue(bot[field])

    def test_format_flag_after_subcommand(self):
        snapshot = ROOT / "data" / "catalog.json"
        if not snapshot.is_file():
            self.skipTest("checked-in catalog snapshot missing")
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = catalog.main(
                ["search", "outbound", "--format", "text", "--catalog", str(snapshot)]
            )
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("addHref:", text)
        self.assertIn("marketplace:", text)
        self.assertIn("grokbot://", text)
        self.assertTrue(text.startswith("Source:"))

    def test_format_flag_before_subcommand_still_works(self):
        snapshot = ROOT / "data" / "catalog.json"
        if not snapshot.is_file():
            self.skipTest("checked-in catalog snapshot missing")
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = catalog.main(
                ["--catalog", str(snapshot), "--format", "json", "search", "outbound"]
            )
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("results", payload)
        self.assertEqual(payload.get("query"), "outbound")


class RefreshWrapperTests(unittest.TestCase):
    def test_ignores_redundant_leading_refresh_arg(self):
        import importlib.util

        path = ROOT / "scripts" / "refresh-catalog.py"
        spec = importlib.util.spec_from_file_location("refresh_catalog", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.extra_args(["refresh-catalog.py"]), [])
        self.assertEqual(mod.extra_args(["refresh-catalog.py", "--list"]), ["--list"])
        self.assertEqual(
            mod.extra_args(["refresh-catalog.py", "refresh", "--format", "json"]),
            ["--format", "json"],
        )


if __name__ == "__main__":
    unittest.main()
