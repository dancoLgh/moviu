import os
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from moviu_server.config import AppConfig
from moviu_server.app import DesktopApp
from moviu_server.setup_wizard import SetupWizard


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "Requires a graphical display")
class SetupWizardTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("1050x680")
        self.root.update()
        self.addCleanup(self.root.destroy)
        patcher = patch("moviu_server.setup_wizard.discover_printers", return_value=["USB", "Etiquetas"])
        self.printers = patcher.start()
        self.addCleanup(patcher.stop)
        self.apply = MagicMock(return_value=True)
        self.cancel = MagicMock()
        self.config = AppConfig()
        self.wizard = SetupWizard(self.root, self.config, self.apply, self.cancel)

    def select_printer(self, name="USB"):
        self.wizard.printer_var.set(name)
        self.wizard._validate_printer()

    def test_odoo_applies_only_after_printer_access_and_final_review(self):
        wizard = self.wizard
        self.assertEqual(wizard.step, "template")
        wizard.next()
        self.assertEqual(wizard.step, "printer")
        self.assertEqual(str(wizard.next_button.cget("state")), "disabled")
        self.select_printer()
        wizard.next()
        self.assertEqual(wizard.step, "access")
        self.assertEqual(wizard.access_var.get(), "local")
        wizard.access_var.set("shared")
        wizard.next()
        self.assertEqual(wizard.step, "review")
        self.assertEqual(wizard.next_button.cget("text"), "Finalizar")
        self.apply.assert_not_called()
        self.assertFalse(self.config.setup_completed)

        wizard.next()

        self.apply.assert_called_once_with("odoo", "USB", "shared")
        self.assertFalse(wizard.winfo_exists())

    def test_chepos_skips_access_step_and_keeps_local_mode(self):
        wizard = self.wizard
        wizard.access_var.set("shared")
        wizard.template_var.set("chepos")
        wizard._template_changed()
        wizard.next()
        self.select_printer("Etiquetas")
        wizard.next()

        self.assertEqual(wizard.step, "review")
        self.assertEqual(wizard.steps, ("template", "printer", "review"))
        wizard.next()

        self.apply.assert_called_once_with("chepos", "Etiquetas", "local")

    def test_missing_printers_block_progress_and_refresh_recovers(self):
        self.printers.return_value = []
        wizard = self.wizard
        wizard.next()
        wizard.next()
        self.assertEqual(wizard.step, "printer")
        self.assertEqual(str(wizard.next_button.cget("state")), "disabled")
        self.apply.assert_not_called()

        self.printers.return_value = ["New USB"]
        wizard.refresh_printers()
        self.select_printer("New USB")
        wizard.next()

        self.assertEqual(wizard.step, "access")

    def test_cancel_and_back_do_not_apply_partial_configuration(self):
        wizard = self.wizard
        wizard.next()
        self.select_printer()
        wizard.next()
        wizard.back()
        self.assertEqual(wizard.step, "printer")
        self.assertEqual(wizard.printer_var.get(), "USB")
        wizard.cancel()

        self.apply.assert_not_called()
        self.cancel.assert_called_once()
        self.assertFalse(self.config.setup_completed)

    def test_failed_apply_leaves_review_open_for_retry(self):
        wizard = self.wizard
        wizard.next()
        self.select_printer()
        wizard.next()
        wizard.next()
        self.apply.return_value = False

        wizard.next()

        self.assertTrue(wizard.winfo_exists())
        self.assertEqual(wizard.step, "review")
        self.assertTrue(wizard.error_var.get())
        self.assertEqual(str(wizard.next_button.cget("state")), "normal")

    def test_refresh_removes_printer_that_is_no_longer_installed(self):
        wizard = self.wizard
        wizard.next()
        self.select_printer()
        self.printers.return_value = ["Etiquetas"]
        wizard.refresh_printers()

        self.assertEqual(wizard.printer_var.get(), "")
        self.assertEqual(str(wizard.next_button.cget("state")), "disabled")


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "Requires a graphical display")
class FirstRunWindowTests(unittest.TestCase):
    def test_first_run_maps_parent_and_wizard_without_blocking_the_event_loop(self):
        def setup_logging(app):
            app.log_handler = MagicMock()
            app.log_handler.drain_pending.return_value = []

        with (
            patch("moviu_server.app.load_config", return_value=AppConfig()),
            patch("moviu_server.app.save_config") as save,
            patch("moviu_server.app.discover_printers", return_value=["USB"]),
            patch("moviu_server.setup_wizard.discover_printers", return_value=["USB"]),
            patch("moviu_server.app.acknowledge_update_startup"),
            patch.object(DesktopApp, "_setup_logging", setup_logging),
            patch.object(DesktopApp, "_register_signal_handlers"),
            patch.object(DesktopApp, "_check_single_instance"),
            patch.object(DesktopApp, "_background_update_check"),
        ):
            app = DesktopApp()
            def cleanup():
                for callback in app.root.tk.call("after", "info"):
                    app.root.after_cancel(callback)
                app.root.destroy()
            self.addCleanup(cleanup)
            app.root.update()

        self.assertTrue(app.root.winfo_viewable())
        self.assertIsNotNone(app._setup_wizard)
        self.assertTrue(app._setup_wizard.winfo_viewable())
        self.assertFalse(app.config.setup_completed)
        self.assertIsNone(app.controller.thread)
        self.assertIsNone(app.bridge_controller.server)
        save.assert_not_called()
