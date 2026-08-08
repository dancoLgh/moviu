import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from moviu_server.app import ServerController
from moviu_server.config import AppConfig


class ServerControllerTests(unittest.TestCase):
    @patch("moviu_server.app._suppress_windows_connection_reset_noise")
    @patch("moviu_server.app._ensure_streams")
    @patch("moviu_server.app.threading.Thread")
    @patch("moviu_server.app.uvicorn.Server")
    @patch("moviu_server.app.uvicorn.Config")
    @patch("moviu_server.app.create_certificate_api", return_value="certificate-app")
    @patch("moviu_server.app.create_api", return_value="https-app")
    @patch("moviu_server.app.ensure_certificates")
    def test_start_and_stop_manage_https_and_isolated_http_servers(
        self,
        ensure_certificates,
        _create_api,
        _create_certificate_api,
        uvicorn_config,
        uvicorn_server,
        thread_class,
        _ensure_streams,
        _suppress_noise,
    ):
        ensure_certificates.return_value = (Path("cert.pem"), Path("key.pem"))
        https_server = SimpleNamespace(started=True, should_exit=False, run=MagicMock())
        certificate_server = SimpleNamespace(started=True, should_exit=False, run=MagicMock())
        uvicorn_server.side_effect = [https_server, certificate_server]
        https_thread = MagicMock()
        certificate_thread = MagicMock()
        https_thread.is_alive.side_effect = [True, False, False]
        certificate_thread.is_alive.side_effect = [True, False, False]
        thread_class.side_effect = [https_thread, certificate_thread]
        controller = ServerController(AppConfig(port=9000))
        controller._log_config = MagicMock(return_value={})

        controller.start()

        self.assertEqual(uvicorn_config.call_count, 2)
        self.assertEqual(uvicorn_config.call_args_list[0].args, ("https-app",))
        self.assertEqual(uvicorn_config.call_args_list[0].kwargs["port"], 9000)
        self.assertEqual(uvicorn_config.call_args_list[0].kwargs["ssl_certfile"], "cert.pem")
        self.assertEqual(uvicorn_config.call_args_list[1].args, ("certificate-app",))
        self.assertEqual(uvicorn_config.call_args_list[1].kwargs["port"], 9001)
        self.assertNotIn("ssl_certfile", uvicorn_config.call_args_list[1].kwargs)
        https_thread.start.assert_called_once_with()
        certificate_thread.start.assert_called_once_with()

        self.assertTrue(controller.stop())

        self.assertTrue(https_server.should_exit)
        self.assertTrue(certificate_server.should_exit)
        self.assertEqual(
            [https_thread.join.call_args, certificate_thread.join.call_args],
            [call(timeout=2), call(timeout=2)],
        )
        self.assertIsNone(controller.server)
        self.assertIsNone(controller.certificate_server)

    @patch("moviu_server.app._suppress_windows_connection_reset_noise")
    @patch("moviu_server.app._ensure_streams")
    @patch("moviu_server.app.threading.Thread")
    @patch("moviu_server.app.uvicorn.Server")
    @patch("moviu_server.app.uvicorn.Config")
    @patch("moviu_server.app.create_certificate_api", return_value="certificate-app")
    @patch("moviu_server.app.create_api", return_value="https-app")
    @patch("moviu_server.app.ensure_certificates")
    def test_second_listener_start_failure_stops_first_listener(
        self,
        ensure_certificates,
        _create_api,
        _create_certificate_api,
        _uvicorn_config,
        uvicorn_server,
        thread_class,
        _ensure_streams,
        _suppress_noise,
    ):
        ensure_certificates.return_value = (Path("cert.pem"), Path("key.pem"))
        https_server = SimpleNamespace(started=False, should_exit=False, run=MagicMock())
        certificate_server = SimpleNamespace(started=False, should_exit=False, run=MagicMock())
        uvicorn_server.side_effect = [https_server, certificate_server]
        https_thread = MagicMock()
        certificate_thread = MagicMock()
        https_thread.is_alive.return_value = False
        certificate_thread.is_alive.return_value = False
        certificate_thread.start.side_effect = RuntimeError("thread failed")
        thread_class.side_effect = [https_thread, certificate_thread]
        controller = ServerController(AppConfig(port=9000))
        controller._log_config = MagicMock(return_value={})

        with self.assertRaisesRegex(RuntimeError, "thread failed"):
            controller.start()

        self.assertTrue(https_server.should_exit)
        self.assertTrue(certificate_server.should_exit)
        self.assertIsNone(controller.server)
        self.assertIsNone(controller.certificate_server)

    def test_stop_forces_exit_before_clearing_slow_server(self):
        server = SimpleNamespace(should_exit=False, force_exit=False)
        thread = MagicMock()
        thread.is_alive.side_effect = [True, True, False]
        controller = ServerController(AppConfig())
        controller.server = server
        controller.thread = thread

        self.assertTrue(controller.stop())

        self.assertTrue(server.should_exit)
        self.assertTrue(server.force_exit)
        self.assertEqual(thread.join.call_args_list, [call(timeout=2), call(timeout=3)])
        self.assertIsNone(controller.server)

    def test_stop_keeps_references_when_thread_does_not_exit(self):
        server = SimpleNamespace(should_exit=False, force_exit=False)
        thread = MagicMock()
        thread.is_alive.return_value = True
        controller = ServerController(AppConfig())
        controller.server = server
        controller.thread = thread

        self.assertFalse(controller.stop())

        self.assertIs(controller.server, server)
        self.assertIs(controller.thread, thread)


if __name__ == "__main__":
    unittest.main()
