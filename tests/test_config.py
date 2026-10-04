import unittest
from dataclasses import asdict

from moviu_server.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def test_existing_configuration_keeps_api_key_required(self):
        config = AppConfig.from_dict({"host": "0.0.0.0", "api_key": "existing-key"})

        self.assertFalse(config.allow_without_api_key)
        self.assertEqual(config.bind_host, "0.0.0.0")
        self.assertEqual(config.api_key, "existing-key")

    def test_no_key_mode_stays_local_across_config_round_trip(self):
        config = AppConfig(host="0.0.0.0", allow_without_api_key=True)
        self.assertEqual(config.bind_host, "127.0.0.1")

        restored = AppConfig.from_dict(asdict(config))

        self.assertTrue(restored.allow_without_api_key)
        self.assertEqual(restored.host, "127.0.0.1")
        self.assertEqual(restored.bind_host, "127.0.0.1")

    def test_loopback_host_is_not_migrated_back_to_lan(self):
        config = AppConfig.from_dict({"host": "127.0.0.1"})

        self.assertEqual(config.bind_host, "127.0.0.1")

    def test_existing_configuration_defaults_to_two_cut_margin_lines(self):
        config = AppConfig.from_dict({})

        self.assertEqual(config.cut_margin_lines, 2)

    def test_invalid_persisted_cut_margin_uses_default(self):
        config = AppConfig.from_dict({"cut_margin_lines": 21})

        self.assertEqual(config.cut_margin_lines, 2)


if __name__ == "__main__":
    unittest.main()
