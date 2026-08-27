import unittest

from moviu_server.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def test_existing_configuration_defaults_to_two_cut_margin_lines(self):
        config = AppConfig.from_dict({})

        self.assertEqual(config.cut_margin_lines, 2)

    def test_invalid_persisted_cut_margin_uses_default(self):
        config = AppConfig.from_dict({"cut_margin_lines": 21})

        self.assertEqual(config.cut_margin_lines, 2)


if __name__ == "__main__":
    unittest.main()
