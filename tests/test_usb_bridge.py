import unittest
from threading import Event
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from moviu_server.config import AppConfig
from moviu_server.configuration_templates import build_template_config
from moviu_server.server import create_api
from moviu_server.usb_bridge import UsbBridgeController
from tcp_usb_bridge.printer_bridge import PrinterServer


class UsbBridgeBindingTests(unittest.TestCase):
    @patch("moviu_server.usb_bridge.discover_printers", return_value=["USB"])
    @patch("tcp_usb_bridge.printer_bridge.send_raw_to_printer")
    def test_template_tcp_destination_reaches_bridge_with_expected_authentication(self, send_raw, _printers):
        for template_id, access in (("odoo", "local"), ("chepos", "local"), ("odoo", "shared"), ("odoo", "shared_without_key")):
            with self.subTest(template=template_id, access=access):
                delivered = Event()
                send_raw.reset_mock()
                send_raw.side_effect = lambda *_args: delivered.set()
                controller = UsbBridgeController()
                controller.start("USB", 0, host="127.0.0.1")
                try:
                    port = controller.server._server.getsockname()[1]
                    config = build_template_config(AppConfig(usb_bridge_port=port), template_id, "USB", access)
                    app = create_api(config)
                    requires_key = not config.allow_without_api_key
                    peer = "192.168.1.25" if config.host == "0.0.0.0" else "127.0.0.1"
                    with TestClient(app, client=(peer, 12345)) as client:
                        payload = {
                            "mode": "raw_text", "content": "Ticket de prueba\n",
                            "printer": {"host": config.printer_host, "port": config.printer_port},
                        }
                        if requires_key:
                            self.assertEqual(client.post("/api/print", json=payload).status_code, 401)
                        response = client.post(
                            "/api/print", json=payload,
                            headers={"X-API-Key": config.api_key} if requires_key else {},
                        )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertTrue(delivered.wait(timeout=2))
                    send_raw.assert_called_once_with("USB", b"\x1bt\x09Ticket de prueba\n")
                finally:
                    controller.stop()

    @patch("moviu_server.usb_bridge.discover_printers", return_value=["USB"])
    @patch("moviu_server.usb_bridge.PrinterServer")
    def test_failed_start_can_be_retried_after_freeing_port(self, server_class, _printers):
        controller = UsbBridgeController()
        failed = MagicMock()
        failed.start.side_effect = OSError("port busy")
        working = MagicMock()
        server_class.side_effect = [failed, working]

        with self.assertRaises(OSError):
            controller.start("USB", 9100, host="127.0.0.1")
        self.assertIsNone(controller.server)
        failed.stop.assert_called_once()

        controller.start("USB", 9100, host="127.0.0.1")

        self.assertIs(controller.server, working)
        working.start.assert_called_once()

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
            host="127.0.0.1",
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
