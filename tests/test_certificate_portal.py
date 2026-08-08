import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from moviu_server.certs import (
    ca_certificate_path,
    certificate_sha256_fingerprint,
    ensure_certificates,
)
from moviu_server.config import AppConfig
from moviu_server.server import certificate_http_port, create_api, create_certificate_api


class CertificatePortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.cert_path = base / "cert.pem"
        self.key_path = base / "key.pem"
        self.config = AppConfig(
            ssl_cert_path=str(self.cert_path),
            ssl_key_path=str(self.key_path),
        )
        ensure_certificates(self.cert_path, self.key_path, ["localhost", "192.168.1.20"])
        self.client = TestClient(create_api(self.config))
        self.http_client = TestClient(create_certificate_api(self.config))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_public_portal_contains_download_and_platform_guides(self):
        response = self.http_client.get("/certificado")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Descargar certificado CA", response.text)
        self.assertIn("Windows", response.text)
        self.assertIn("Android", response.text)
        self.assertIn("Linux", response.text)

    def test_platform_selector_exposes_keyboard_focus_and_regions(self):
        response = self.http_client.get("/certificado")

        self.assertIn(":focus-visible", response.text)
        self.assertIn('role="group" aria-label="Sistema operativo"', response.text)
        self.assertIn('role="region" aria-labelledby="windows-label"', response.text)
        self.assertIn(
            certificate_sha256_fingerprint(ca_certificate_path(self.cert_path)),
            response.text,
        )
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_download_link_is_relative_and_does_not_trust_host_header(self):
        response = self.http_client.get("/certificado", headers={"host": "attacker.example"})

        self.assertIn('href="/certificado/descargar"', response.text)
        self.assertNotIn('href="http://attacker.example', response.text)

    def test_installation_steps_keep_text_in_the_content_column(self):
        response = self.http_client.get("/certificado")
        page = BeautifulSoup(response.text, "html.parser")

        steps = page.select(".panel li")
        self.assertEqual(len(steps), 12)
        self.assertTrue(
            all(
                step.find("div", class_="step-content", recursive=False) is not None
                for step in steps
            )
        )
        self.assertEqual(len(page.select("code.command")), 3)

    def test_public_download_returns_only_ca_certificate(self):
        response = self.http_client.get("/certificado/descargar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, ca_certificate_path(self.cert_path).read_bytes())
        self.assertIn("moviu-ca.crt", response.headers["content-disposition"])
        self.assertEqual(response.headers["content-type"], "application/x-x509-ca-cert")
        self.assertNotEqual(response.content, self.key_path.read_bytes())

    def test_download_returns_404_when_ca_is_missing(self):
        ca_certificate_path(self.cert_path).unlink()

        response = self.http_client.get("/certificado/descargar")

        self.assertEqual(response.status_code, 404)

    def test_http_app_exposes_no_api_or_documentation_routes(self):
        for path in ("/api/print", "/api/health", "/api/discover", "/docs", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.http_client.get(path).status_code, 404)

    def test_certificate_routes_are_not_exposed_by_https_api_app(self):
        self.assertEqual(self.client.get("/certificado").status_code, 404)
        self.assertEqual(self.client.get("/certificado/descargar").status_code, 404)

    def test_http_port_is_next_to_https_port(self):
        self.assertEqual(certificate_http_port(9000), 9001)
        with self.assertRaises(ValueError):
            certificate_http_port(65535)


if __name__ == "__main__":
    unittest.main()
