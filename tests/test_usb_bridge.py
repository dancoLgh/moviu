import unittest
from unittest.mock import MagicMock, patch

from moviu_server.usb_bridge import UsbBridgeController
from tcp_usb_bridge.printer_bridge import PrinterServer


class UsbBridgeBindingTests(unittest.TestCase):
    @patch("moviu_server.usb_bridge.discover_printers", return_value=["USB"])
    @patch("moviu_server.usb_bridge.PrinterServer")
    def test_local_bridge_uses_loopback_socket(self, server_class, _printers):
        controller = UsbBridgeController()

        controller.start("USB", 9100, host="127.0.0.1")

        server_class.assert_called_once_with("USB", "127.0.0.1", 9100, controller._notify_status)
        server_class.return_value.start.assert_called_once()

    @patch("tcp_usb_bridge.printer_bridge.send_raw_to_printer")
    def test_stopped_bridge_discards_pending_job_from_old_connection(self, send_raw):
        server = PrinterServer("USB", "0.0.0.0", 9100)
        client = MagicMock()
        client.recv.side_effect = [b"pending job", b""]

        server._handle_client(client, ("192.168.1.25", 12345))

        send_raw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
