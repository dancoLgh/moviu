import os
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from moviu_server.app import DesktopApp
from moviu_server.config import AppConfig
from moviu_server.ui_state import moviu_connection_addresses
from tests.test_app_settings import Value


class SimpleModeTests(unittest.TestCase):
    def test_addresses_contain_only_host_or_host_and_port(self):
        for host, expected in (("0.0.0.0", "192.168.1.20"), ("127.0.0.1", "127.0.0.1"), ("localhost", "127.0.0.1")):
            with self.subTest(host=host):
                self.assertEqual(moviu_connection_addresses(host, 9000, "192.168.1.20"), (expected, f"{expected}:9000"))
        self.assertEqual(moviu_connection_addresses("::1", 9000, "192.168.1.20"), ("::1", "[::1]:9000"))

    @patch("moviu_server.app.get_local_ip", return_value="192.168.1.20")
    def test_clipboard_uses_running_server_address_and_never_copies_url_scheme(self, _local_ip):
        app = object.__new__(DesktopApp)
        app.config = AppConfig(host="127.0.0.1", port=9999)
        app.controller = SimpleNamespace(server=SimpleNamespace(config=SimpleNamespace(host="0.0.0.0", port=9000)))
        app.root = MagicMock()
        app.simple_ip_var = Value("")
        app.simple_ip_port_var = Value("")
        app.simple_copy_status_var = Value("")
        app._copy_moviu_ip()
        app.root.clipboard_append.assert_called_with("192.168.1.20")
        app._copy_moviu_ip(include_port=True)
        app.root.clipboard_append.assert_called_with("192.168.1.20:9000")

    def test_large_action_starts_or_stops_the_existing_server(self):
        app = object.__new__(DesktopApp)
        app.start_server = MagicMock()
        app.stop_server = MagicMock()
        app.controller = SimpleNamespace(thread=None)
        app._toggle_simple_server()
        app.start_server.assert_called_once()
        app.stop_server.assert_not_called()
        app.controller.thread = SimpleNamespace(is_alive=lambda: True)
        app._toggle_simple_server()
        app.stop_server.assert_called_once()


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "Requires a graphical display")
class SimpleModeWindowTests(unittest.TestCase):
    def make_app(self, mode):
        def setup_logging(app):
            app.log_handler = MagicMock()
            app.log_handler.drain_pending.return_value = []

        with (
            patch("moviu_server.app.load_config", return_value=AppConfig(setup_completed=True, default_interface_mode=mode)),
            patch("moviu_server.app.discover_printers", return_value=["USB"]),
            patch("moviu_server.app.acknowledge_update_startup"),
            patch.object(DesktopApp, "_setup_logging", setup_logging),
            patch.object(DesktopApp, "_register_signal_handlers"),
            patch.object(DesktopApp, "_check_single_instance"),
            patch.object(DesktopApp, "_background_update_check"),
            patch.object(DesktopApp, "_apply_autostart"),
        ):
            app = DesktopApp()
            app.root.update()
        def cleanup():
            for callback in app.root.tk.call("after", "info"):
                app.root.after_cancel(callback)
            app.root.destroy()
        self.addCleanup(cleanup)
        return app

    def test_simple_mode_hides_advanced_ui_and_shares_live_status_and_activity(self):
        app = self.make_app("simple")
        self.assertTrue(app.simple_shell.winfo_viewable())
        self.assertFalse(app.layout_shell.winfo_viewable())
        app.server_badge_var.set("Iniciando")
        self.assertEqual(str(app.simple_action_btn.cget("state")), "disabled")
        app.server_badge_var.set("Servidor activo")
        self.assertEqual(app.simple_action_var.get(), "Detener servidor")
        app.server_badge_var.set("Servidor detenido")
        self.assertEqual(app.simple_action_var.get(), "Iniciar servidor")
        app.activity_feed.add("INFO", "Impresión enviada", 1)
        app._refresh_activity_summary()
        self.assertEqual(app.activity_message_vars[0].get(), "Impresión enviada")

        def labels(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TLabel":
                    yield child
                yield from labels(child)
        self.assertTrue(any(str(label.cget("textvariable")) == str(app.activity_message_vars[0]) for label in labels(app.simple_shell)))
        app._show_interface_mode("advanced")
        app.root.update()
        self.assertTrue(app.layout_shell.winfo_viewable())
        self.assertFalse(app.simple_shell.winfo_viewable())
        self.assertEqual(app.activity_message_vars[0].get(), "Impresión enviada")
        app._show_interface_mode("simple")
        self.assertEqual(app.default_interface_mode_var.get(), "simple")

    def test_advanced_startup_respects_saved_preference(self):
        app = self.make_app("advanced")
        self.assertTrue(app.layout_shell.winfo_viewable())
        self.assertFalse(app.simple_shell.winfo_viewable())
        self.assertEqual(app._interface_mode, "advanced")
