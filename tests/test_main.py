import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class MainEntryPointTests(unittest.TestCase):
    def test_packaged_self_test_loads_ssl_runtime(self):
        self.assertEqual(main.packaged_self_test(), 0)

    def test_packaged_self_test_writes_requested_attestation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            marker = Path(temp_dir) / "self-test"
            environment = {
                "MOVIU_SELF_TEST_FILE": str(marker),
                "MOVIU_SELF_TEST_TOKEN": "expected-token",
            }
            with patch.dict(os.environ, environment):
                self.assertEqual(main.packaged_self_test(), 0)

            self.assertEqual(marker.read_text(encoding="ascii"), "expected-token")

    @patch("main.packaged_self_test", side_effect=ImportError("missing native module"))
    def test_self_test_exits_cleanly_when_runtime_import_fails(self, _self_test):
        with patch.object(main.sys, "argv", ["MoviuPrintServer", "--self-test"]):
            with self.assertRaises(SystemExit) as raised:
                main.main()

        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
