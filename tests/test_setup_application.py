import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from moviu_server.app import DesktopApp
from moviu_server.config import AppConfig
from tests.test_app_settings import Value, make_app


def make_setup_app(server_running=False):
    app = make_app(server_running)
    app.root = MagicMock()
    app.api_key_var = Value(app.config.api_key)
    app.controller.start = MagicMock()
    app._show_interface_mode = MagicMock()
    return app


class ApplyTemplateTests(unittest.TestCase):
    def setUp(self):
        warning = patch("moviu_server.app.messagebox.showwarning")
        self.warning = warning.start()
        self.addCleanup(warning.stop)

    @patch("moviu_server.app.open_local_network_ports")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_finishing_local_template_saves_and_starts_without_opening_firewall(self, _printers, save, firewall):
        for template_id in ("odoo", "chepos"):
            with self.subTest(template_id=template_id):
                app = make_setup_app()

                self.assertTrue(app.apply_configuration_template(template_id, "USB", "local"))

                self.assertTrue(app.config.setup_completed)
                self.assertEqual(app.config.configuration_template, template_id)
                self.assertEqual(app.controller.config, app.config)
                self.assertEqual(app.printer_host_var.get(), "127.0.0.1")
                self.assertEqual(app.port_var.get(), str(app.config.port))
                self.assertTrue(app.server_autostart_var.get())
                self.assertTrue(app.bridge_autostart_var.get())
                self.assertTrue(app.bridge_enabled_var.get())
                self.assertEqual(app.bridge_printer_var.get(), "USB")
                self.assertEqual(app.printer_port_var.get(), app.bridge_port_var.get())
                app.bridge_controller.start.assert_called_once_with("USB", 9100, host="127.0.0.1")
                app.start_server.assert_called_once_with(save=False)
                save.assert_called_with(app.config)
                firewall.assert_not_called()

    @patch("moviu_server.app.open_local_network_ports")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_sharing_replaces_existing_listeners_and_opens_only_configured_ports(self, _printers, _save, firewall):
        app = make_setup_app(server_running=True)
        app.config.allow_without_api_key = True
        app.bridge_controller.server = SimpleNamespace(printer_name="Old USB", port=9100, host="127.0.0.1")

        self.assertTrue(app.apply_configuration_template("odoo", "USB", "shared"))

        self.assertFalse(app.config.allow_without_api_key)
        self.assertEqual(app.config.bind_host, "0.0.0.0")
        app.stop_server.assert_called_once()
        app.stop_bridge.assert_called_once()
        app.bridge_controller.start.assert_called_once_with("USB", 9100, host="0.0.0.0")
        firewall.assert_called_once_with(9000, 9100, certificate_port=9001)

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=[])
    def test_disappeared_printer_does_not_mark_setup_complete_or_stop_services(self, _printers, save, error):
        app = make_setup_app(server_running=True)

        self.assertFalse(app.apply_configuration_template("odoo", "USB", "local"))

        self.assertFalse(app.config.setup_completed)
        save.assert_not_called()
        app.stop_server.assert_not_called()
        app.stop_bridge.assert_not_called()
        error.assert_called_once()

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_shutdown_failure_does_not_persist_or_start_replacements(self, _printers, save, _error):
        app = make_setup_app(server_running=True)
        app.stop_server.return_value = False

        self.assertFalse(app.apply_configuration_template("odoo", "USB", "local"))

        save.assert_not_called()
        app.stop_bridge.assert_not_called()
        app.bridge_controller.start.assert_not_called()
        app.start_server.assert_not_called()
        self.assertFalse(app.config.setup_completed)

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_bridge_failure_keeps_setup_pending(self, _printers, save, _error):
        app = make_setup_app()
        app.bridge_controller.start.side_effect = OSError("port already in use")

        self.assertFalse(app.apply_configuration_template("odoo", "USB", "local"))

        self.assertFalse(app.config.setup_completed)
        save.assert_not_called()
        app.start_server.assert_not_called()

    @patch("moviu_server.app.messagebox.showerror")
    @patch("moviu_server.app.save_config", side_effect=OSError("disk full"))
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_persistence_failure_restores_preexisting_bridge_and_server(self, _printers, _save, _error):
        app = make_setup_app(server_running=True)
        original = app.config
        app.bridge_controller.server = SimpleNamespace(printer_name="Old USB", port=9200, host="0.0.0.0")

        self.assertFalse(app.apply_configuration_template("odoo", "USB", "local"))

        self.assertIs(app.config, original)
        self.assertFalse(app.config.setup_completed)
        self.assertEqual(app.bridge_controller.start.call_args_list[-1].args, ("Old USB", 9200))
        self.assertEqual(app.bridge_controller.start.call_args_list[-1].kwargs, {"host": "0.0.0.0"})
        app.start_server.assert_called_once_with(save=False)

    @patch("moviu_server.app.messagebox.showwarning")
    @patch("moviu_server.app.open_local_network_ports", side_effect=OSError("access denied"))
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_firewall_failure_reports_pending_access_without_losing_configuration(self, _printers, _save, _firewall, warning):
        app = make_setup_app()

        self.assertTrue(app.apply_configuration_template("odoo", "USB", "shared"))

        self.assertTrue(app.config.setup_completed)
        self.assertEqual(app.config.host, "0.0.0.0")
        warning.assert_called_once()

    def test_template_server_autostart_is_independent_of_windows_startup(self):
        app = make_setup_app()
        app.config.server_autostart = True
        app.config.auto_start = False

        app._maybe_autostart_server()

        app.root.after.assert_called_once_with(200, app.start_server)

    @patch("moviu_server.app.open_local_network_ports")
    @patch("moviu_server.app.save_config")
    @patch("moviu_server.app.discover_printers", return_value=["USB"])
    def test_shared_template_without_key_opens_lan_and_simple_interface(self, _printers, _save, firewall):
        app = make_setup_app()
        self.assertTrue(app.apply_configuration_template("odoo", "USB", "shared_without_key"))
        self.assertTrue(app.config.allow_without_api_key)
        self.assertEqual(app.config.bind_host, "0.0.0.0")
        app.bridge_controller.start.assert_called_once_with("USB", 9100, host="0.0.0.0")
        app._show_interface_mode.assert_called_once_with("simple")
        firewall.assert_called_once_with(9000, 9100, certificate_port=9001)
        self.warning.assert_called_once()

    @patch("moviu_server.app.save_config")
    def test_initial_printer_scan_does_not_persist_settings(self, save):
        app = make_setup_app()
        app.available_printers = []
        app.printer_combo = MagicMock()
        with patch("moviu_server.app.discover_printers", return_value=["USB"]):
            app.refresh_printers(initial=True)

        save.assert_not_called()
        self.assertFalse(app.config.setup_completed)


class StartupSetupTests(unittest.TestCase):
    def test_only_new_installations_open_the_wizard_before_autostart(self):
        for completed in (False, True):
            with self.subTest(completed=completed):
                app = object.__new__(DesktopApp)
                # Exercise the real constructor while isolating OS, UI and network effects.
                with (
                    patch("moviu_server.app.tk.Tk", return_value=MagicMock()),
                    patch("moviu_server.app.load_config", return_value=AppConfig(setup_completed=completed, auto_start=True)),
                    patch("moviu_server.app.acknowledge_update_startup"),
                    patch.object(DesktopApp, "_setup_logging"),
                    patch.object(DesktopApp, "_set_window_icon"),
                    patch.object(DesktopApp, "_setup_theme"),
                    patch.object(DesktopApp, "_build_ui"),
                    patch.object(DesktopApp, "_maximize_window"),
                    patch.object(DesktopApp, "_configure_window_hooks"),
                    patch.object(DesktopApp, "_register_signal_handlers"),
                    patch.object(DesktopApp, "_check_single_instance"),
                    patch.object(DesktopApp, "_apply_autostart") as autostart,
                    patch.object(DesktopApp, "_maybe_autostart_server") as server,
                    patch.object(DesktopApp, "_maybe_autostart_bridge") as bridge,
                ):
                    app.__init__()
                if completed:
                    autostart.assert_called_once()
                    server.assert_called_once()
                    bridge.assert_called_once()
                    app.root.after_idle.assert_not_called()
                else:
                    app.root.after_idle.assert_called_once_with(app.open_setup_wizard)
                    autostart.assert_not_called()
                    server.assert_not_called()
                    bridge.assert_not_called()
