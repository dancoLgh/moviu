from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class HeroDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html, "html.parser")

    def test_hero_uses_a_compact_headline_without_forced_breaks(self):
        heading = self.soup.select_one(".hero h1")

        self.assertEqual(heading.get_text(" ", strip=True), "Tu web imprime local.")
        self.assertIsNone(heading.find("br"))

    def test_lucide_replaces_hand_drawn_interface_icons(self):
        icon_script = self.soup.find("script", src=lambda src: src and "lucide" in src)

        self.assertIsNotNone(icon_script)
        self.assertTrue(icon_script.has_attr("async"))
        self.assertGreaterEqual(len(self.soup.select("[data-lucide]")), 25)
        self.assertNotIn("<svg", self.html)

    def test_icon_only_controls_have_text_fallbacks(self):
        self.assertEqual(
            [fallback.get_text(strip=True) for fallback in self.soup.select(".icon-fallback")],
            ["Menú", "Cerrar"],
        )

    def test_copy_label_is_updated_without_replacing_its_icon(self):
        script = (SITE / "script.js").read_text(encoding="utf-8")
        styles = (SITE / "styles.css").read_text(encoding="utf-8")

        self.assertIsNotNone(self.soup.select_one("[data-copy-code] [data-copy-label]"))
        self.assertNotIn('copyButton.textContent = "Copiado"', script)
        self.assertIn('copyLabel.textContent = "Copiado"', script)
        self.assertNotIn(".code-header i {", styles)
        self.assertIn(".code-header > div > i {", styles)

    def test_real_moviu_mark_is_used_for_branding(self):
        mark_path = SITE / "assets" / "moviu-mark.png"

        self.assertGreaterEqual(len(self.soup.select('img[src="assets/moviu-mark.png"]')), 4)
        with Image.open(mark_path) as mark:
            self.assertEqual(mark.format, "PNG")
            self.assertEqual(mark.size, (256, 256))


if __name__ == "__main__":
    unittest.main()
