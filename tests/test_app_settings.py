import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from moviu_server.app import DesktopApp
from moviu_server.config import AppConfig


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


def make_app(server_running: bool) -> DesktopApp:
    app = object.__new__(DesktopApp)
    app.config = AppConfig()
    thread = SimpleNamespace(is_alive=lambda: server_running) if server_running else None
    app.controller = SimpleNamespace(thread=thread)
    app.host_var = Value("0.0.0.0")
    app.port_var = Value("9001")
    app.printer_host_var = Value("192.168.1.50")
    app.printer_port_var = Value("9100")
    app.printer_width_var = Value("384 (58mm)")
    app.printer_gamma_var = Value(600)
    app.simulate_var = Value(True)
    app.auto_start_var = Value(False)
    app.bridge_enabled_var = Value(False)
    app.bridge_port_var = Value("9100")
    app.bridge_printer_var = Value("")
    app.bridge_autostart_var = Value(False)
    app.github_token_var = Value("")
    app._apply_autostart = MagicMock()
    app._update_endpoint_url = MagicMock()
    app.stop_server = MagicMock(return_value=True)
    app.start_server = MagicMock()
    return app


class SaveSettingsTests(unittest.TestCase):
    @patch("moviu_server.app.messagebox.showinfo")
    @patch("moviu_server.app.save_config")
    def test_running_server_is_restarted_after_settings_change(self, save_config, showinfo):
        app = make_app(server_running=True)

        self.assertTrue(app.save_settings())

        self.assertEqual(app.config.port, 9001)
        self.assertEqual(app.config.printer_width, 384)
        save_config.assert_called_once_with(app.config)
        app.stop_server.assert_called_once_with()
        app.start_server.assert_called_once_with()
        app._update_endpoint_url.assert_not_called()
        self.assertIn("reiniciando", showinfo.call_args.args[1])

    @patch("moviu_server.app.messagebox.showinfo")
    @patch("moviu_server.app.save_config")
    def test_stopped_server_updates_display_without_restart(self, _save_config, _showinfo):
        app = make_app(server_running=False)

        self.assertTrue(app.save_settings())

        app.stop_server.assert_not_called()
        app.start_server.assert_not_called()
        app._update_endpoint_url.assert_called_once_with()

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.messagebox.showinfo")
    @patch("moviu_server.app.save_config")
    def test_failed_shutdown_does_not_start_replacement_server(
        self, _save_config, _showinfo, showerror
    ):
        app = make_app(server_running=True)
        app.stop_server.return_value = False

        self.assertFalse(app.save_settings())

        app.start_server.assert_not_called()
        showerror.assert_called_once()


class NetworkAccessSettingsTests(unittest.TestCase):
    @patch("moviu_server.app.messagebox.showinfo")
    @patch("moviu_server.app.messagebox.askyesno", return_value=True)
    @patch("moviu_server.app.open_local_network_ports")
    def test_firewall_uses_new_ports_after_settings_are_saved(
        self, open_ports, _askyesno, _showinfo
    ):
        open_ports.return_value = SimpleNamespace(
            firewall="test",
            rules_changed=True,
        )
        app = object.__new__(DesktopApp)
        app.config = AppConfig(host="0.0.0.0", port=9001)
        app.controller = SimpleNamespace(
            server=SimpleNamespace(config=SimpleNamespace(host="0.0.0.0", port=9000))
        )
        app.bridge_controller = SimpleNamespace(server=None)
        app.save_settings = MagicMock(return_value=True)

        app.enable_local_network_access()

        open_ports.assert_called_once_with(9001, None, certificate_port=9002)

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    def test_rejects_https_port_without_room_for_http_port(self, save_config, showerror):
        app = make_app(server_running=False)
        app.port_var = Value("65535")

        self.assertFalse(app.save_settings())

        save_config.assert_not_called()
        showerror.assert_called_once()

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    def test_rejects_port_collisions_between_managed_listeners(self, save_config, showerror):
        app = make_app(server_running=False)
        app.bridge_enabled_var = Value(True)
        app.bridge_port_var = Value("9002")

        self.assertFalse(app.save_settings())

        save_config.assert_not_called()
        showerror.assert_called_once()

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    def test_rejects_certificate_port_reserved_for_single_instance(self, save_config, showerror):
        app = make_app(server_running=False)
        app.port_var = Value("29169")

        self.assertFalse(app.save_settings())

        save_config.assert_not_called()
        showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
