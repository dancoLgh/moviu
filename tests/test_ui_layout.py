import unittest
from pathlib import Path


APP_SOURCE = (Path(__file__).resolve().parents[1] / "moviu_server" / "app.py").read_text(
    encoding="utf-8"
)


class ConfigurationLayoutTests(unittest.TestCase):
    def test_bridge_autostart_has_single_configuration_owner(self):
        self.assertEqual(APP_SOURCE.count("variable=self.bridge_autostart_var"), 1)

    def test_bridge_is_first_expanded_advanced_section(self):
        bridge = 'self._accordion(content, "bridge", "Puente USB", expanded=True)'
        network = 'self._accordion(content, "network", "Acceso de red")'

        self.assertLess(APP_SOURCE.index(bridge), APP_SOURCE.index(network))

    def test_connection_save_is_in_page_footer(self):
        self.assertIn(
            'text="Guarda la red antes de regenerar certificados o habilitar el firewall."',
            APP_SOURCE,
        )
        self.assertNotIn('text="Guardar red"', APP_SOURCE)


if __name__ == "__main__":
    unittest.main()
