import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from moviu_server.app import CHANGELOG_PATH, DesktopApp, RELEASES_URL
from moviu_server.config import VERSION
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
        app.root = MagicMock()
        return app

    @patch("moviu_server.app.ReleaseNotesDialog")
    def test_changelog_displays_complete_bundled_history(self, release_notes_dialog):
        app = self.make_app()
        content = "# Changelog\n\n## [1.4.0]\n- Actualización\n\n## [1.0.0]\n- Inicial\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            changelog = Path(temp_dir) / "CHANGELOG.md"
            changelog.write_text(content, encoding="utf-8")
            with patch("moviu_server.app.CHANGELOG_PATH", changelog):
                app._show_changelog()

        release_notes_dialog.assert_called_once_with(
            app.root, f"Novedades - v{VERSION.lstrip('v')}", content
        )

    def test_changelog_path_points_to_complete_project_history(self):
        content = CHANGELOG_PATH.read_text(encoding="utf-8")

        self.assertIn(f"## [{VERSION.lstrip('v')}]", content)
        self.assertIn("## [1.0.0]", content)

    @patch("moviu_server.app.ReleaseNotesDialog")
    @patch("moviu_server.app.open_release_page")
    def test_changelog_opens_releases_when_bundled_file_is_missing(
        self, open_release_page, release_notes_dialog
    ):
        app = self.make_app()

        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "CHANGELOG.md"
            with patch("moviu_server.app.CHANGELOG_PATH", missing):
                app._show_changelog()

        open_release_page.assert_called_once_with(RELEASES_URL)
        release_notes_dialog.assert_not_called()

    @patch("moviu_server.app.ReleaseNotesDialog")
    @patch("moviu_server.app.open_release_page")
    def test_changelog_opens_releases_when_bundled_file_is_invalid(
        self, open_release_page, release_notes_dialog
    ):
        app = self.make_app()

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "CHANGELOG.md"
            invalid.write_bytes(b"\xff")
            with patch("moviu_server.app.CHANGELOG_PATH", invalid):
                app._show_changelog()

        open_release_page.assert_called_once_with(RELEASES_URL)
        release_notes_dialog.assert_not_called()

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
