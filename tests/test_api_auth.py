import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from moviu_server.config import AppConfig
from moviu_server.server import create_api


class ApiAuthenticationTests(unittest.TestCase):
    def setUp(self):
        processor_patch = patch("moviu_server.server.PrintProcessor")
        self.processor = processor_patch.start().return_value
        self.addCleanup(processor_patch.stop)
        self.processor.process.return_value = {"status": "sent", "bytes": 4}
        self.payload = {"mode": "raw_text", "content": "test"}

    def test_default_mode_requires_correct_key_for_local_and_lan_clients(self):
        app = create_api(AppConfig(api_key="secret"))
        for peer in ("127.0.0.1", "192.168.1.25"):
            with self.subTest(peer=peer), TestClient(app, client=(peer, 12345)) as client:
                for headers in ({}, {"X-API-Key": "wrong"}):
                    self.assertEqual(client.post("/api/print", json=self.payload, headers=headers).status_code, 401)
                self.processor.process.assert_not_called()
                self.assertEqual(
                    client.post("/api/print", json=self.payload, headers={"X-API-Key": "secret"}).status_code,
                    200,
                )
                self.processor.process.reset_mock()

    def test_local_mode_accepts_prints_without_key_from_loopback(self):
        app = create_api(AppConfig(allow_without_api_key=True))
        for peer in ("127.0.0.1", "::1"):
            with self.subTest(peer=peer), TestClient(app, client=(peer, 12345)) as client:
                response = client.post("/api/print", json=self.payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "sent")
                self.assertEqual(client.get("/api/health").status_code, 200)

    def test_local_mode_rejects_remote_peer_even_with_key_and_forwarded_headers(self):
        app = create_api(AppConfig(api_key="secret", allow_without_api_key=True))
        for peer in ("192.168.1.25", "::ffff:192.168.1.25", "testclient"):
            with self.subTest(peer=peer), TestClient(app, client=(peer, 12345)) as client:
                for headers in ({}, {
                    "X-API-Key": "secret",
                    "X-Forwarded-For": "127.0.0.1",
                    "Forwarded": "for=127.0.0.1",
                }):
                    self.assertEqual(client.post("/api/print", json=self.payload, headers=headers).status_code, 403)
                    self.assertEqual(client.get("/api/health", headers=headers).status_code, 403)
                    self.assertEqual(client.get("/api/printers", headers=headers).status_code, 403)
        self.processor.process.assert_not_called()

    def test_mode_changes_do_not_remove_authentication_from_existing_listener(self):
        config = AppConfig(api_key="secret")
        app = create_api(config)
        config.allow_without_api_key = True

        with TestClient(app, client=("192.168.1.25", 12345)) as client:
            self.assertEqual(client.post("/api/print", json=self.payload).status_code, 401)
        self.processor.process.assert_not_called()

    def test_browser_preflight_allows_printing_from_local_web_app(self):
        app = create_api(AppConfig(allow_without_api_key=True))
        with TestClient(app, client=("127.0.0.1", 12345)) as client:
            response = client.options("/api/print", headers={
                "Origin": "https://pos.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")


if __name__ == "__main__":
    unittest.main()
