import unittest
from types import SimpleNamespace
from unittest.mock import patch

from moviu_server.app import DesktopApp
from moviu_server.updater import WEBSITE_DOWNLOAD_URL, check_for_updates


class UpdateDestinationTests(unittest.TestCase):
    @patch("moviu_server.updater.get_latest_release_info")
    def test_new_release_points_to_website_download_section(self, release_info):
        release_info.return_value = {
            "tag_name": "v99.0.0",
            "html_url": "https://github.com/dancoLgh/moviu/releases/tag/v99.0.0",
        }

        available, version, url = check_for_updates()

        self.assertTrue(available)
        self.assertEqual(version, "v99.0.0")
        self.assertEqual(url, WEBSITE_DOWNLOAD_URL)
        self.assertEqual(url, "https://dancolgh.github.io/moviu/#descargas")

    @patch("moviu_server.app.open_release_page")
    @patch("moviu_server.app.messagebox.askyesno", return_value=True)
    @patch("moviu_server.app.check_for_updates")
    def test_accepting_update_opens_website_download_section(
        self,
        check_updates,
        _askyesno,
        open_page,
    ):
        check_updates.return_value = (True, "v99.0.0", WEBSITE_DOWNLOAD_URL)
        app = object.__new__(DesktopApp)
        app.config = SimpleNamespace(github_token="")

        app._manual_update_check()

        open_page.assert_called_once_with(WEBSITE_DOWNLOAD_URL)


if __name__ == "__main__":
    unittest.main()
