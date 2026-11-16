import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from moviu_server.config import AppConfig, load_config, save_config
from moviu_server.configuration_templates import (
    ConfigurationTemplate,
    build_template_config,
)


class ConfigurationTemplateTests(unittest.TestCase):
    def test_local_templates_enable_bridge_and_disable_key_without_sharing(self):
        for template_id in ("odoo", "chepos"):
            with self.subTest(template_id=template_id):
                base = AppConfig(printer_host="192.168.1.50", simulate_printer=True)
                config = build_template_config(base, template_id, "Ticket USB")

                self.assertEqual(config.host, "127.0.0.1")
                self.assertEqual(config.bind_host, "127.0.0.1")
                self.assertTrue(config.allow_without_api_key)
                self.assertEqual(config.printer_host, "127.0.0.1")
                self.assertEqual(config.printer_port, config.usb_bridge_port)
                self.assertEqual(config.usb_bridge_printer, "Ticket USB")
                self.assertTrue(config.usb_bridge_enabled)
                self.assertTrue(config.usb_bridge_autostart)
                self.assertTrue(config.server_autostart)
                self.assertFalse(config.auto_start, "Do not add Windows startup implicitly")
                self.assertFalse(config.simulate_printer)
                self.assertTrue(config.setup_completed)
                self.assertEqual(config.configuration_template, template_id)
                self.assertEqual(config.default_interface_mode, "simple")
                self.assertFalse(base.setup_completed)
                self.assertFalse(base.usb_bridge_enabled)

    def test_shared_odoo_requires_key_and_listens_on_lan(self):
        base = AppConfig(allow_without_api_key=True, api_key="existing-key")

        config = build_template_config(base, "odoo", "USB", "shared")
        restored = AppConfig.from_dict(asdict(config))

        self.assertEqual(restored.bind_host, "0.0.0.0")
        self.assertFalse(restored.allow_without_api_key)
        self.assertEqual(restored.api_key, "existing-key")

    def test_shared_odoo_generates_key_if_previous_key_was_empty(self):
        config = build_template_config(AppConfig(api_key=""), "odoo", "USB", "shared")

        self.assertTrue(config.api_key)
        self.assertNotEqual(AppConfig().api_key, AppConfig().api_key)

    def test_chepos_cannot_be_shared_through_its_template(self):
        with self.assertRaises(ValueError):
            build_template_config(AppConfig(), "chepos", "USB", "shared")

    def test_odoo_shared_without_key_preserves_lan_after_reloading(self):
        config = build_template_config(AppConfig(), "odoo", "USB", "shared_without_key")
        restored = AppConfig.from_dict(asdict(config))
        self.assertTrue(restored.allow_without_api_key)
        self.assertEqual(restored.bind_host, "0.0.0.0")

    def test_template_can_select_advanced_interface_by_default(self):
        template = ConfigurationTemplate("community", "Community POS", "Otra integración", default_interface_mode="advanced")
        with patch("moviu_server.configuration_templates.CONFIGURATION_TEMPLATES", (template,)):
            config = build_template_config(AppConfig(), "community", "USB")
        self.assertEqual(config.default_interface_mode, "advanced")

    def test_invalid_choices_and_port_collisions_do_not_mutate_config(self):
        for template, printer, mode, port in (
            ("unknown", "USB", "local", 9100),
            ("odoo", "  ", "local", 9100),
            ("odoo", "USB", "unknown", 9100),
            ("odoo", "USB", "local", 9000),
            ("odoo", "USB", "local", 9001),
            ("odoo", "USB", "local", 29170),
            ("odoo", "USB", "local", 65536),
        ):
            with self.subTest(template=template, printer=printer, mode=mode, port=port):
                base = AppConfig(usb_bridge_port=port)
                before = asdict(base)
                with self.assertRaises(ValueError):
                    build_template_config(base, template, printer, mode)
                self.assertEqual(asdict(base), before)

    def test_community_template_uses_the_same_builder(self):
        template = ConfigurationTemplate("community", "Community POS", "Otra integración")
        with patch("moviu_server.configuration_templates.CONFIGURATION_TEMPLATES", (template,)):
            config = build_template_config(AppConfig(), "community", "USB")

        self.assertEqual(config.configuration_template, "community")
        self.assertTrue(config.allow_without_api_key)


class SetupPersistenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.config_file = self.directory / "config.json"
        for target, value in (("CONFIG_DIR", self.directory), ("CONFIG_FILE", self.config_file)):
            patcher = patch(f"moviu_server.config.{target}", value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_first_run_stays_pending_after_relaunch_until_completed(self):
        first = load_config()
        self.assertFalse(first.setup_completed)
        self.assertFalse(load_config().setup_completed)

        save_config(build_template_config(first, "chepos", "USB"))
        restored = load_config()

        self.assertTrue(restored.setup_completed)
        self.assertEqual(restored.configuration_template, "chepos")
        self.assertTrue(restored.usb_bridge_autostart)
        self.assertTrue(restored.server_autostart)

    def test_existing_installation_is_not_forced_through_setup(self):
        self.config_file.write_text(json.dumps({
            "host": "192.168.1.20", "api_key": "existing-key",
            "printer_host": "192.168.1.50", "auto_start": True,
        }))

        config = load_config()

        self.assertTrue(config.setup_completed)
        self.assertEqual(config.configuration_template, "")
        self.assertEqual(config.host, "192.168.1.20")
        self.assertEqual(config.printer_host, "192.168.1.50")
        self.assertEqual(config.api_key, "existing-key")
        self.assertTrue(config.auto_start)

    def test_failed_save_preserves_previous_file_and_cleans_temporary_file(self):
        save_config(AppConfig(api_key="original"))
        original_contents = self.config_file.read_text()

        with patch("moviu_server.config.json.dump", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                save_config(AppConfig(api_key="replacement"))

        self.assertEqual(self.config_file.read_text(), original_contents)
        self.assertEqual(list(self.directory.iterdir()), [self.config_file])
