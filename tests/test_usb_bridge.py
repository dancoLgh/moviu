import unittest
from threading import Event
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from moviu_server.config import AppConfig
from moviu_server.server import create_api
from moviu_server.usb_bridge import UsbBridgeController
from tcp_usb_bridge.printer_bridge import PrinterServer


class UsbBridgeBindingTests(unittest.TestCase):
    @patch("moviu_server.usb_bridge.discover_printers", return_value=["USB"])
    @patch("tcp_usb_bridge.printer_bridge.send_raw_to_printer")
    def test_api_without_key_sends_job_through_real_local_usb_bridge(self, send_raw, _printers):
        delivered = Event()
        send_raw.side_effect = lambda *_args: delivered.set()
        controller = UsbBridgeController()
        controller.start("USB", 0, host="127.0.0.1")
        server = controller.server
        self.addCleanup(controller.stop)
        port = server._server.getsockname()[1]
        config = AppConfig(
            allow_without_api_key=True,
            usb_bridge_enabled=True,
            usb_bridge_printer="USB",
            usb_bridge_port=port,
        )
        app = create_api(config)
        payload = {
            "mode": "raw_text",
            "content": "Prueba por puente USB\n",
            "printer": {"host": "127.0.0.1", "port": port},
        }

        with TestClient(app, client=("127.0.0.1", 12345)) as client:
            response = client.post("/api/print", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "sent")
        self.assertTrue(delivered.wait(timeout=2), "Job did not reach the USB bridge")
        send_raw.assert_called_once_with("USB", b"\x1bt\x09Prueba por puente USB\n")
        with TestClient(app, client=("192.168.1.25", 12345)) as client:
            self.assertEqual(client.post("/api/print", json=payload).status_code, 403)
        self.assertEqual(send_raw.call_count, 1)

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
