import base64
import io
import unittest

from PIL import Image
from fastapi.testclient import TestClient

from moviu_server.config import AppConfig
from moviu_server.escpos import image_to_escpos
from moviu_server.printer import PrintJob, PrintProcessor
from moviu_server.server import create_api


class EscposCutMarginTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("1", (8, 1), 1)

    def test_adds_configured_feed_before_cut(self):
        payload = image_to_escpos(self.image, cut_margin_lines=5)

        self.assertTrue(payload.endswith(b"\n\n\n\n\n\x1dV0"))

    def test_rejects_cut_margin_outside_supported_range(self):
        with self.assertRaisesRegex(ValueError, "entre 0 y 20"):
            image_to_escpos(self.image, cut_margin_lines=21)

    def test_processor_allows_job_to_override_global_margin(self):
        processor = PrintProcessor("127.0.0.1", 9100, cut_margin_lines=3)
        job = PrintJob(
            mode="image",
            content=self._image_base64(),
            printer_host="127.0.0.1",
            printer_port=9100,
            cut_margin_lines=6,
        )

        payload, _preview = processor._build_payload(job)

        self.assertTrue(payload.endswith(b"\n" * 6 + b"\x1dV0"))

    def test_processor_uses_global_margin_without_override(self):
        processor = PrintProcessor("127.0.0.1", 9100, cut_margin_lines=4)
        job = PrintJob(
            mode="image",
            content=self._image_base64(),
            printer_host="127.0.0.1",
            printer_port=9100,
        )

        payload, _preview = processor._build_payload(job)

        self.assertTrue(payload.endswith(b"\n" * 4 + b"\x1dV0"))

    def test_disabling_cut_does_not_add_margin(self):
        payload = image_to_escpos(self.image, cut=False, cut_margin_lines=5)

        self.assertFalse(payload.endswith(b"\n" * 5 + b"\x1dV0"))

    def test_existing_positional_simulate_argument_is_preserved(self):
        processor = PrintProcessor("127.0.0.1", 9100, 576, 500, True)

        self.assertTrue(processor.simulate)
        self.assertEqual(processor.cut_margin_lines, 2)

    def test_api_accepts_margin_override(self):
        config = AppConfig(api_key="test-key", simulate_printer=True)
        client = TestClient(create_api(config))
        request = {
            "mode": "image",
            "content": self._image_base64(),
            "cut_margin_lines": 5,
        }

        response = client.post(
            "/api/print",
            headers={"X-API-Key": "test-key"},
            json=request,
        )
        request["cut_margin_lines"] = 0
        response_without_margin = client.post(
            "/api/print",
            headers={"X-API-Key": "test-key"},
            json=request,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_without_margin.status_code, 200)
        self.assertEqual(
            response.json()["bytes"],
            response_without_margin.json()["bytes"] + 5,
        )

    def test_api_rejects_margin_above_limit(self):
        config = AppConfig(api_key="test-key", simulate_printer=True)
        client = TestClient(create_api(config))

        response = client.post(
            "/api/print",
            headers={"X-API-Key": "test-key"},
            json={
                "mode": "image",
                "content": self._image_base64(),
                "cut_margin_lines": 21,
            },
        )

        self.assertEqual(response.status_code, 422)

    def _image_base64(self):
        output = io.BytesIO()
        self.image.save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode("ascii")


if __name__ == "__main__":
    unittest.main()
