from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.add(element_id)
        if tag == "a" and (href := attributes.get("href")):
            self.links.append(href)
        if tag == "script" and (src := attributes.get("src")):
            self.scripts.append(src)
        if (
            tag == "link"
            and attributes.get("rel") == "stylesheet"
            and (href := attributes.get("href"))
        ):
            self.stylesheets.append(href)


class GitHubPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_local_assets_exist(self) -> None:
        for asset in self.parser.scripts + self.parser.stylesheets:
            parsed = urlparse(asset)
            if not parsed.scheme:
                self.assertTrue((SITE / parsed.path).is_file(), asset)

    def test_internal_navigation_targets_exist(self) -> None:
        for link in self.parser.links:
            if link.startswith("#") and len(link) > 1:
                self.assertIn(link[1:], self.parser.ids, link)

    def test_downloads_use_release_artifact_names(self) -> None:
        expected = {
            "MoviuPrintServer-Windows-x86_64.exe",
            "MoviuPrintServer-Linux-x86_64",
        }
        download_names = {
            Path(urlparse(link).path).name
            for link in self.parser.links
            if "/releases/latest/download/" in link
        }
        self.assertEqual(download_names, expected)

    def test_core_message_is_present(self) -> None:
        plain_text = re.sub(r"<[^>]+>", " ", self.html).lower()
        self.assertIn("100% construido con vibe coding", plain_text)
        self.assertIn("qz tray", plain_text)
        self.assertIn("jsprintmanager", plain_text)
        self.assertIn("certificado", plain_text)
        self.assertIn("odoo iot", plain_text)
        self.assertIn("sin depender de odoo iot", plain_text)
        self.assertIn("punto de venta", plain_text)
        self.assertIn("back office", plain_text)
        self.assertIn("addons que conectan esos flujos con moviu", plain_text)

    def test_odoo_addons_contact_is_available(self) -> None:
        self.assertIn("mailto:daniel@dawnpy.com", self.parser.links)
        self.assertIn('data-lucide="puzzle"', self.html)
        self.assertIn('data-lucide="mail"', self.html)

    def test_pages_workflow_deploys_site_directory(self) -> None:
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertRegex(workflow, r"path:\s*site")
        self.assertLess(
            workflow.index("python -m unittest tests.test_site"),
            workflow.index("actions/deploy-pages@v4"),
        )

    def test_content_remains_visible_without_javascript(self) -> None:
        stylesheet = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertRegex(stylesheet, r"\.reveal\s*\{\s*opacity:\s*1")
        self.assertIn(".enhanced .reveal", stylesheet)


if __name__ == "__main__":
    unittest.main()
