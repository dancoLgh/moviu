import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from moviu_server.app import DesktopApp
from moviu_server.updater import WEBSITE_DOWNLOAD_URL


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class ImmediateThread:
    def __init__(self, target, daemon):
        self.target = target

    def start(self):
        self.target()


class DesktopUpdateFlowTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(DesktopApp)
        app.config = SimpleNamespace(github_token="")
        app.github_token_var = Value("")
        app.update_link_var = Value("")
        app._update_busy = False
        app._closing = False
        app._queue_ui_callback = MagicMock()
        app._download_and_install_update = MagicMock()
        return app

    @patch("moviu_server.app.open_release_page")
    @patch("moviu_server.app.self_update_support")
    @patch("moviu_server.app.messagebox.askyesno", return_value=True)
    def test_source_execution_offers_manual_download(
        self, _ask_yes_no, update_support, open_page
    ):
        update_support.return_value = (False, "Código fuente")
        app = self.make_app()

        app._handle_update_check({"tag_name": "v99.0.0"}, "")

        open_page.assert_called_once_with(WEBSITE_DOWNLOAD_URL)
        app._download_and_install_update.assert_not_called()

    @patch("moviu_server.app.self_update_support", return_value=(True, ""))
    @patch("moviu_server.app.messagebox.askyesno", return_value=True)
    def test_packaged_execution_downloads_update(self, _ask_yes_no, _update_support):
        app = self.make_app()
        release = {"tag_name": "v99.0.0"}

        app._handle_update_check(release, "token")

        app._download_and_install_update.assert_called_once_with(release, "token")

    @patch("moviu_server.app.threading.Thread", ImmediateThread)
    @patch("moviu_server.app.download_update")
    def test_downloaded_file_is_removed_if_app_closes_during_download(self, download):
        app = self.make_app()
        app._download_and_install_update = DesktopApp._download_and_install_update.__get__(app)
        app._closing = True
        with tempfile.TemporaryDirectory() as temp_dir:
            staged = Path(temp_dir) / "update.bin"
            staged.write_bytes(b"update")
            download.return_value = staged

            app._download_and_install_update({"tag_name": "v99.0.0"}, "")

            self.assertFalse(staged.exists())
            app._queue_ui_callback.assert_not_called()

    def test_staged_cleanup_error_does_not_block_shutdown_path(self):
        app = self.make_app()
        staged = MagicMock()
        staged.unlink.side_effect = OSError("locked")
        app._staged_update_path = staged

        app._cleanup_staged_update()

        self.assertIsNone(app._staged_update_path)


if __name__ == "__main__":
    unittest.main()
