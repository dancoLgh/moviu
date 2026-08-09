from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class DownloadDonationModalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.script = (SITE / "script.js").read_text(encoding="utf-8")
        cls.core = (SITE / "download-modal-core.js").read_text(encoding="utf-8")
        cls.styles = (SITE / "styles.css").read_text(encoding="utf-8")

    def test_binary_links_open_the_download_modal(self):
        self.assertEqual(self.html.count("data-download data-platform="), 2)
        self.assertIn("data-download-modal", self.html)
        self.assertIn('role="dialog"', self.html)
        self.assertIn('aria-modal="true"', self.html)

    def test_all_provided_donation_amounts_are_available(self):
        for amount in ("5", "10", "20", "100"):
            self.assertIn(f'data-donation-amount="{amount}"', self.html)
            self.assertIn(f'data-dlocal-amount="{amount}"', self.html)

    def test_official_dlocal_go_sdk_and_checkout_are_used(self):
        self.assertIn("https://static.dlocalgo.com/dlocalgo.min.js", self.script)
        self.assertIn("DKGuMAOMKKGaGHsreDzGCdYmGjNMCJKs", self.script)
        self.assertIn("new DlocalGo", self.script)
        self.assertIn('typeof DlocalGo === "function"', self.script)
        self.assertIn('currency: "USD"', self.script)
        self.assertIn("normalizeDonationAmount(amount)", self.script)

    def test_site_declares_a_local_favicon(self):
        self.assertIn('rel="icon" href="favicon.svg"', self.html)
        self.assertTrue((SITE / "favicon.svg").is_file())

    def test_download_is_not_conditional_on_donation(self):
        self.assertIn("createDownloadScheduler", self.script)
        self.assertIn("onStart: triggerDownload", self.script)
        self.assertIn("options.duration ?? 3", self.core)
        self.assertIn("La donación es opcional", self.html)

    def test_modal_has_mobile_styles(self):
        self.assertIn(".download-modal", self.styles)
        self.assertIn(".donation-amounts", self.styles)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript tests")
    def test_download_scheduler_behavior(self):
        subprocess.run(
            ["node", "--test", "tests/js/download_modal_core.test.js"],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
