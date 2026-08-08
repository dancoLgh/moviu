import io
import logging
import logging.config
import tempfile
import unittest
from pathlib import Path

from moviu_server.logging_config import build_uvicorn_log_config


class UvicornLoggingConfigTests(unittest.TestCase):
    def test_access_records_propagate_without_special_formatter_fields(self):
        captured: list[str] = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        root_logger = logging.getLogger()
        capture_handler = CaptureHandler()
        root_logger.addHandler(capture_handler)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config = build_uvicorn_log_config(
                    Path(temp_dir) / "app.log",
                    io.StringIO(),
                )
                logging.config.dictConfig(config)
                logging.getLogger("uvicorn.access").info(
                    '%s - "%s %s HTTP/%s" %d',
                    "127.0.0.1:1234",
                    "GET",
                    "/health",
                    "1.1",
                    200,
                )
        finally:
            root_logger.removeHandler(capture_handler)
            logging.shutdown()

        self.assertEqual(
            captured,
            ['127.0.0.1:1234 - "GET /health HTTP/1.1" 200'],
        )

    def test_error_records_reach_desktop_root_handlers(self):
        captured: list[str] = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        root_logger = logging.getLogger()
        capture_handler = CaptureHandler()
        root_logger.addHandler(capture_handler)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config = build_uvicorn_log_config(
                    Path(temp_dir) / "app.log",
                    io.StringIO(),
                )
                logging.config.dictConfig(config)
                logging.getLogger("uvicorn.error").error("Address already in use")
        finally:
            root_logger.removeHandler(capture_handler)
            logging.shutdown()

        self.assertEqual(captured, ["Address already in use"])


if __name__ == "__main__":
    unittest.main()
