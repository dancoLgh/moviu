import threading
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
        app._update_dialog = MagicMock()
        app._show_update_progress = MagicMock()
        app._update_install_lock = threading.Lock()
        app._update_thread = None
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

    @patch("moviu_server.app.threading.Thread")
    def test_update_worker_is_non_daemon_so_shutdown_cannot_orphan_files(self, thread):
        app = self.make_app()
        app._download_and_install_update = DesktopApp._download_and_install_update.__get__(app)

        app._download_and_install_update({"tag_name": "v99.0.0"}, "")

        thread.assert_called_once()
        self.assertFalse(thread.call_args.kwargs["daemon"])
        thread.return_value.start.assert_called_once_with()

    @patch("moviu_server.app.threading.Thread", ImmediateThread)
    @patch("moviu_server.app.launch_self_update")
    @patch("moviu_server.app.verify_staged_update")
    @patch("moviu_server.app.download_update")
    def test_downloaded_executable_is_self_tested_before_install(
        self, download, verify, launch
    ):
        app = self.make_app()
        app._download_and_install_update = DesktopApp._download_and_install_update.__get__(app)
        with tempfile.TemporaryDirectory() as temp_dir:
            staged = Path(temp_dir) / "update.bin"
            staged.write_bytes(b"update")
            download.return_value = staged

            app._download_and_install_update({"tag_name": "v99.0.0"}, "")

        verify.assert_called_once_with(staged)
        launch.assert_called_once_with(staged)
        self.assertIsNone(app._staged_update_path)

    @patch("moviu_server.app.threading.Thread", ImmediateThread)
    @patch("moviu_server.app.launch_self_update")
    @patch("moviu_server.app.verify_staged_update")
    @patch("moviu_server.app.download_update")
    def test_closing_during_self_test_prevents_install(self, download, verify, launch):
        app = self.make_app()
        app._download_and_install_update = DesktopApp._download_and_install_update.__get__(app)
        verify.side_effect = lambda _path: setattr(app, "_closing", True)
        with tempfile.TemporaryDirectory() as temp_dir:
            staged = Path(temp_dir) / "update.bin"
            staged.write_bytes(b"update")
            download.return_value = staged

            app._download_and_install_update({"tag_name": "v99.0.0"}, "")

            self.assertFalse(staged.exists())
        launch.assert_not_called()

    def test_staged_cleanup_error_does_not_block_shutdown_path(self):
        app = self.make_app()
        staged = MagicMock()
        staged.unlink.side_effect = OSError("locked")
        app._staged_update_path = staged

        app._cleanup_staged_update()

        self.assertIsNone(app._staged_update_path)

    def test_update_progress_is_forwarded_to_dialog(self):
        app = self.make_app()

        app._update_progress_dialog("Verificando integridad SHA-256...", 0, None)

        app._update_dialog.set_progress.assert_called_once_with(
            "Verificando integridad SHA-256...", 0, None
        )

    @patch("moviu_server.app.UpdateProgressDialog")
    def test_update_progress_dialog_opens_for_selected_version(self, dialog):
        app = self.make_app()
        app._update_dialog = None
        app._show_update_progress = DesktopApp._show_update_progress.__get__(app)

        app._show_update_progress("v99.0.0")

        dialog.assert_called_once_with(app.root, "v99.0.0")
        self.assertIs(app._update_dialog, dialog.return_value)

    def test_finished_update_shows_success_before_scheduled_restart(self):
        app = self.make_app()

        app._finish_update_install("v99.0.0")

        app._update_dialog.complete.assert_called_once_with()
        app.root.after.assert_called_once_with(1200, app._do_exit)


if __name__ == "__main__":
    unittest.main()
