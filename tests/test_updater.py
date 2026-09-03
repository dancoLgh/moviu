import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from moviu_server.updater import (
    CHECKSUM_ASSET_NAME,
    WEBSITE_DOWNLOAD_URL,
    UpdateError,
    _SafeRedirectHandler,
    _download_asset,
    _linux_update_script,
    acknowledge_update_startup,
    check_for_updates,
    download_update,
    is_newer_release,
    launch_self_update,
    select_release_asset,
    self_update_support,
    verify_staged_update,
)


WINDOWS_ASSET = "MoviuPrintServer-Windows-x86_64.exe"


class UpdateMetadataTests(unittest.TestCase):
    @patch("moviu_server.updater.get_latest_release_info")
    def test_new_release_points_to_manual_download_fallback(self, release_info):
        release_info.return_value = {
            "tag_name": "v99.0.0",
            "html_url": "https://github.com/dancoLgh/moviu/releases/tag/v99.0.0",
        }

        available, version, url = check_for_updates()

        self.assertTrue(available)
        self.assertEqual(version, "v99.0.0")
        self.assertEqual(url, WEBSITE_DOWNLOAD_URL)

    def test_only_strictly_newer_stable_versions_are_accepted(self):
        self.assertTrue(is_newer_release({"tag_name": "v2.0.0"}, "1.9.9"))
        self.assertFalse(is_newer_release({"tag_name": "v1.9.9"}, "1.9.9"))
        self.assertFalse(is_newer_release({"tag_name": "invalid"}, "1.9.9"))
        self.assertFalse(
            is_newer_release({"tag_name": "v2.0.0", "prerelease": True}, "1.9.9")
        )

    def test_selects_asset_for_supported_platform(self):
        asset = {"name": WINDOWS_ASSET, "url": "https://api.example/windows"}

        selected = select_release_asset(
            {"assets": [asset]}, platform_name="win32", machine="AMD64"
        )

        self.assertIs(selected, asset)

    def test_rejects_unsupported_architecture(self):
        with self.assertRaisesRegex(UpdateError, "plataforma"):
            select_release_asset({}, platform_name="linux", machine="arm64")


class UpdateDownloadTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"new moviu executable"
        self.checksum = hashlib.sha256(self.payload).hexdigest()
        self.release = {
            "tag_name": "v99.0.0",
            "assets": [
                {
                    "name": WINDOWS_ASSET,
                    "url": "https://api.example/windows",
                    "size": len(self.payload),
                },
                {
                    "name": CHECKSUM_ASSET_NAME,
                    "url": "https://api.example/checksums",
                },
            ],
        }

    @patch("moviu_server.updater._download_asset")
    def test_downloads_and_verifies_release_binary(self, download_asset):
        checksum_file = f"{self.checksum}  {WINDOWS_ASSET}\n".encode()
        download_asset.side_effect = [checksum_file, self.payload]
        progress = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            staged = download_update(
                self.release,
                Path(temp_dir),
                platform_name="win32",
                machine="x86_64",
                progress_callback=progress,
            )

            self.assertEqual(staged.read_bytes(), self.payload)
            self.assertEqual(staged.suffix, ".exe")
            messages = [call.args[0] for call in progress.call_args_list]
            self.assertEqual(messages[0], "Descargando archivo de verificación...")
            self.assertIn("Verificando integridad SHA-256...", messages)
            self.assertEqual(messages[-1], "Descarga verificada correctamente")

    @patch("moviu_server.updater._download_asset")
    def test_rejects_binary_with_wrong_checksum(self, download_asset):
        checksum_file = f"{'0' * 64}  {WINDOWS_ASSET}\n".encode()
        download_asset.side_effect = [checksum_file, self.payload]

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(UpdateError, "SHA-256"):
                download_update(
                    self.release,
                    Path(temp_dir),
                    platform_name="win32",
                    machine="x86_64",
                )

    @patch("moviu_server.updater.urllib.request.build_opener")
    def test_asset_download_reports_streamed_byte_progress(self, build_opener):
        response = MagicMock()
        response.headers = {"Content-Length": "6"}
        response.read.side_effect = [b"abc", b"def", b""]
        build_opener.return_value.open.return_value.__enter__.return_value = response
        progress = MagicMock()

        payload = _download_asset(
            {"url": "https://github.com/download", "size": 6},
            progress_callback=progress,
        )

        self.assertEqual(payload, b"abcdef")
        self.assertEqual(
            [call.args for call in progress.call_args_list],
            [(3, 6), (6, 6)],
        )


class SelfUpdateInstallerTests(unittest.TestCase):
    @patch("moviu_server.updater.subprocess.run")
    def test_staged_executable_passes_self_test_in_clean_environment(self, run):
        staged = Path("/opt/moviu/.moviu-update.bin")

        def confirm_self_test(*_args, **kwargs):
            marker = Path(kwargs["env"]["MOVIU_SELF_TEST_FILE"])
            marker.write_text(kwargs["env"]["MOVIU_SELF_TEST_TOKEN"], encoding="ascii")
            return MagicMock(returncode=0)

        run.side_effect = confirm_self_test

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("moviu_server.updater.CONFIG_DIR", Path(temp_dir)):
                verify_staged_update(staged)

        self.assertEqual(run.call_args.args[0], [str(staged), "--self-test"])
        self.assertEqual(
            run.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1"
        )

    @patch("moviu_server.updater.subprocess.run")
    def test_staged_executable_is_rejected_when_self_test_fails(self, run):
        run.return_value.returncode = 1

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("moviu_server.updater.CONFIG_DIR", Path(temp_dir)):
                with self.assertRaisesRegex(UpdateError, "prueba de arranque segura"):
                    verify_staged_update(Path("/opt/moviu/.moviu-update.bin"))

    @patch("moviu_server.updater.subprocess.run")
    def test_staged_executable_must_attest_that_self_test_ran(self, run):
        run.return_value.returncode = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("moviu_server.updater.CONFIG_DIR", Path(temp_dir)):
                with self.assertRaisesRegex(UpdateError, "prueba de arranque segura"):
                    verify_staged_update(Path("/opt/moviu/.moviu-update.bin"))

    @patch("moviu_server.updater.sys.frozen", False, create=True)
    def test_source_execution_uses_manual_update(self):
        supported, reason = self_update_support()

        self.assertFalse(supported)
        self.assertIn("código fuente", reason)

    @patch("moviu_server.updater.secrets.token_hex", return_value="a" * 32)
    @patch("moviu_server.updater.subprocess.Popen")
    def test_windows_installer_is_launched_detached(self, popen, _token_hex):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "José"
            directory.mkdir()
            config_dir = directory / "config"
            executable = directory / "MoviuPrintServer.exe"
            staged = directory / ".moviu-update.exe"
            executable.write_bytes(b"old")
            staged.write_bytes(b"new")
            process = MagicMock()
            popen.side_effect = lambda *_args, **_kwargs: (
                (config_dir / f"moviu-update-armed-{'a' * 32}").write_text(
                    "a" * 32, encoding="ascii"
                ),
                process,
            )[1]

            with patch("moviu_server.updater.CONFIG_DIR", config_dir):
                launch_self_update(
                    staged,
                    executable=executable,
                    parent_pid=123,
                    platform_name="win32",
                )

        command = popen.call_args.args[0]
        self.assertEqual(command[0], "powershell.exe")
        self.assertTrue(command[-1].endswith(".ps1"))
        script = Path(command[-1]).read_text(encoding="utf-8-sig")
        self.assertIn("José", script)
        self.assertIn("La nueva versión no confirmó el arranque", script)
        self.assertIn("if ($backupCreated)", script)
        reset_environment = "$env:PYINSTALLER_RESET_ENVIRONMENT = '1'"
        self.assertIn(reset_environment, script)
        self.assertLess(
            script.index(reset_environment),
            script.index("Start-Process -FilePath $target"),
        )

    def test_linux_restarts_use_a_fresh_pyinstaller_environment(self):
        script = _linux_update_script(
            Path("/opt/moviu/MoviuPrintServer"),
            Path("/opt/moviu/.moviu-update.bin"),
            Path("/tmp/moviu-ready"),
            Path("/tmp/moviu-armed"),
            "a" * 32,
            123,
        )

        export_environment = (
            "PYINSTALLER_RESET_ENVIRONMENT=1\nexport PYINSTALLER_RESET_ENVIRONMENT"
        )
        self.assertIn(export_environment, script)
        self.assertLess(
            script.index(export_environment),
            script.index("/opt/moviu/MoviuPrintServer"),
        )

    @unittest.skipUnless(sys.platform == "linux", "Requiere un entorno Linux")
    def test_linux_installer_replaces_and_restarts_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            marker = directory / "started.txt"
            executable = directory / "MoviuPrintServer"
            staged = directory / ".moviu-update.bin"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            staged.write_text(
                f"#!/bin/sh\nprintf updated > {marker}\n"
                "printf %s \"${MOVIU_UPDATE_READY_FILE##*-}\" > \"$MOVIU_UPDATE_READY_FILE\"\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            staged.chmod(0o755)
            parent = subprocess.Popen(["sleep", "0.1"])

            with patch("moviu_server.updater.CONFIG_DIR", directory / "config"):
                helper = launch_self_update(
                    staged,
                    executable=executable,
                    parent_pid=parent.pid,
                    platform_name="linux",
                )
            parent.wait(timeout=2)
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.05)

            self.assertEqual(marker.read_text(encoding="utf-8"), "updated")
            self.assertIn("printf updated", executable.read_text(encoding="utf-8"))
            helper.wait(timeout=5)

    @unittest.skipUnless(sys.platform == "linux", "Requiere un entorno Linux")
    def test_linux_installer_restores_previous_executable_after_failed_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            marker = directory / "started.txt"
            executable = directory / "MoviuPrintServer"
            staged = directory / ".moviu-update.bin"
            original = f"#!/bin/sh\nprintf old > {marker}\n"
            executable.write_text(original, encoding="utf-8")
            staged.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            executable.chmod(0o755)
            staged.chmod(0o755)
            parent = subprocess.Popen(["sleep", "0.1"])

            with patch("moviu_server.updater.CONFIG_DIR", directory / "config"):
                helper = launch_self_update(
                    staged,
                    executable=executable,
                    parent_pid=parent.pid,
                    platform_name="linux",
                )
            parent.wait(timeout=2)
            helper.wait(timeout=5)
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.05)

            self.assertEqual(executable.read_text(encoding="utf-8"), original)
            self.assertEqual(marker.read_text(encoding="utf-8"), "old")

    @patch("moviu_server.updater.tempfile.NamedTemporaryFile", side_effect=OSError("full"))
    def test_helper_creation_failure_is_reported_as_update_error(self, _temporary_file):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            executable = directory / "MoviuPrintServer"
            staged = directory / ".moviu-update.bin"
            executable.write_bytes(b"old")
            staged.write_bytes(b"new")

            with patch("moviu_server.updater.CONFIG_DIR", directory / "config"):
                with self.assertRaisesRegex(UpdateError, "crear el instalador"):
                    launch_self_update(
                        staged,
                        executable=executable,
                        parent_pid=123,
                        platform_name="linux",
                    )

    def test_startup_acknowledgement_only_writes_safe_temp_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()
            invalid_marker = Path(temp_dir) / f"moviu-update-ready-{'a' * 32}"
            with patch("moviu_server.updater.CONFIG_DIR", config_dir):
                with patch.dict(os.environ, {"MOVIU_UPDATE_READY_FILE": str(invalid_marker)}):
                    acknowledge_update_startup()
                self.assertFalse(invalid_marker.exists())

                marker = config_dir / f"moviu-update-ready-{'b' * 32}"
                with patch.dict(os.environ, {"MOVIU_UPDATE_READY_FILE": str(marker)}):
                    acknowledge_update_startup()
                self.assertEqual(marker.read_text(encoding="ascii"), "b" * 32)

    def test_redirect_handler_rejects_non_github_destination(self):
        request = urllib.request.Request(
            "https://api.github.com/repos/dancoLgh/moviu/releases/assets/1",
            headers={"Authorization": "Bearer secret"},
        )

        with self.assertRaisesRegex(UpdateError, "destino no permitido"):
            _SafeRedirectHandler().redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://example.com/update.exe",
            )

    def test_redirect_handler_strips_token_when_github_origin_changes(self):
        request = urllib.request.Request(
            "https://api.github.com/repos/dancoLgh/moviu/releases/assets/1",
            headers={"Authorization": "Bearer secret"},
        )

        redirected = _SafeRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://release-assets.githubusercontent.com/update.exe",
        )

        self.assertIsNotNone(redirected)
        self.assertIsNone(redirected.get_header("Authorization"))

if __name__ == "__main__":
    unittest.main()
