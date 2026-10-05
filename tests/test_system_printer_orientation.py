import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from moviu_server import system_printer


class SystemPrinterOrientationTests(unittest.TestCase):
    def print_job(self, **options):
        devmode = SimpleNamespace(Fields=0, Orientation=1, PaperSize=9)
        constants = SimpleNamespace(
            DMPAPER_A5=11, DM_PAPERSIZE=2, DM_PAPERWIDTH=8, DM_PAPERLENGTH=4,
            DM_ORIENTATION=1, DMORIENT_PORTRAIT=1, DMORIENT_LANDSCAPE=2,
            HORZRES=8, VERTRES=10,
        )
        printer = Mock()
        printer.GetPrinter.return_value = {'pDevMode': devmode}
        dc = Mock()
        dc.GetDeviceCaps.side_effect = [1000, 1400]
        ui = Mock()
        ui.CreateDCFromHandle.return_value = dc
        ui.CreateDC.return_value = dc
        gui = Mock()
        with (
            patch.object(system_printer.platform, 'system', return_value='Windows'),
            patch.object(system_printer, 'win32print', printer),
            patch.object(system_printer, 'win32con', constants),
            patch.object(system_printer, 'win32ui', ui),
            patch.object(system_printer, 'win32gui', gui),
            patch.object(system_printer, 'ImageWin', Mock()),
            patch.object(system_printer, '_render_pdf_to_images', return_value=[SimpleNamespace(size=(600, 800))]),
        ):
            result = system_printer.print_pdf_to_system_printer(b'%PDF', 'Brother', **options)
        dc.EndDoc.assert_called_once()
        dc.DeleteDC.assert_called_once()
        return result, devmode, gui, printer, ui

    def test_a5_and_both_orientations_are_applied_to_job_device_context(self):
        for orientation, code in [('portrait', 1), ('landscape', 2)]:
            with self.subTest(orientation=orientation):
                result, devmode, gui, printer, _ = self.print_job(paper_size='A5', orientation=orientation)
                self.assertEqual(devmode.PaperSize, 11)
                self.assertEqual(devmode.Orientation, code)
                self.assertEqual(devmode.Fields & 3, 3)
                self.assertEqual(result['orientation'], orientation)
                self.assertEqual(result['paper_size'], 'A5')
                gui.CreateDC.assert_called_once_with('WINSPOOL', 'Brother', devmode)
                printer.ClosePrinter.assert_called_once()
                printer.SetPrinter.assert_not_called()

    def test_orientation_without_size_keeps_existing_paper(self):
        _, devmode, _, _, _ = self.print_job(orientation='landscape')
        self.assertEqual(devmode.PaperSize, 9)
        self.assertEqual(devmode.Fields, 1)
        self.assertEqual(devmode.Orientation, 2)

    def test_custom_paper_with_orientation_preserves_dimensions(self):
        _, devmode, _, _, _ = self.print_job(
            paper_width_mm=148, paper_height_mm=210, orientation='landscape',
        )
        self.assertEqual((devmode.PaperWidth, devmode.PaperLength), (1480, 2100))
        self.assertEqual(devmode.Orientation, 2)

    def test_omitted_orientation_keeps_driver_default(self):
        result, devmode, _, _, _ = self.print_job(paper_size='A5')
        self.assertEqual(devmode.Orientation, 1)
        self.assertFalse(devmode.Fields & 1)
        self.assertNotIn('orientation', result)

    def test_unconfigured_job_uses_native_printer_context(self):
        _, _, gui, _, ui = self.print_job()
        gui.CreateDC.assert_not_called()
        ui.CreateDC.return_value.CreatePrinterDC.assert_called_once_with('Brother')

    def test_invalid_orientation_fails_before_printing(self):
        with self.assertRaisesRegex(system_printer.SystemPrinterError, 'orientation'):
            system_printer.print_pdf_to_system_printer(b'%PDF', 'Brother', orientation='sideways')
