import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from moviu_server.config import AppConfig
from moviu_server.server import create_api


class PdfOrientationApiTests(unittest.TestCase):
    def test_pdf_forwards_a5_orientation_to_system_driver(self):
        with patch('moviu_server.server.print_pdf_to_system_printer') as print_pdf:
            with TestClient(create_api(AppConfig(api_key='test-key'))) as client:
                for orientation in ('portrait', 'landscape'):
                    print_pdf.return_value = {'status': 'sent', 'paper_size': 'A5', 'orientation': orientation}
                    response = client.post('/api/print', headers={'X-API-Key': 'test-key'}, json={
                        'mode': 'pdf', 'content': 'JVBERg==', 'printer': {'name': 'Brother'},
                        'paper_size': 'A5', 'orientation': orientation,
                    })
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['orientation'], orientation)
                    print_pdf.assert_called_with(
                        b'%PDF', 'Brother', dpi=150, paper_size='A5',
                        paper_width_mm=None, paper_height_mm=None, orientation=orientation,
                    )

    def test_invalid_orientation_is_rejected_without_printing(self):
        with patch('moviu_server.server.print_pdf_to_system_printer') as print_pdf:
            with TestClient(create_api(AppConfig(api_key='test-key'))) as client:
                response = client.post('/api/print', headers={'X-API-Key': 'test-key'}, json={
                    'mode': 'pdf', 'content': 'JVBERg==', 'printer': {'name': 'Brother'},
                    'orientation': 'sideways',
                })
                self.assertEqual(response.status_code, 422)
            print_pdf.assert_not_called()
