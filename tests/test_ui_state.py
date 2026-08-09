import unittest

from moviu_server.ui_state import (
    ActivityFeed,
    NAV_ITEMS,
    certificate_portal_url,
    printer_route_label,
    tooltip_coordinates,
)


class ActivityFeedTests(unittest.TestCase):
    def test_feed_returns_newest_events_first(self):
        feed = ActivityFeed(max_events=3)
        feed.add("INFO", "primero", 1)
        feed.add("WARNING", "segundo", 2)

        events = feed.recent()

        self.assertEqual([event.message for event in events], ["segundo", "primero"])

    def test_feed_discards_oldest_events_at_capacity(self):
        feed = ActivityFeed(max_events=2)
        feed.add("INFO", "uno", 1)
        feed.add("INFO", "dos", 2)
        feed.add("INFO", "tres", 3)

        self.assertEqual([event.message for event in feed.recent(5)], ["tres", "dos"])

    def test_feed_rejects_invalid_capacity(self):
        with self.assertRaises(ValueError):
            ActivityFeed(0)

    def test_navigation_destinations_are_unique(self):
        destinations = [destination for destination, _label in NAV_ITEMS]

        self.assertEqual(len(destinations), len(set(destinations)))
        self.assertEqual(
            destinations,
            ["home", "printers", "connection", "activity", "settings", "help"],
        )

    def test_certificate_portal_uses_client_facing_host_and_next_port(self):
        self.assertEqual(
            certificate_portal_url("0.0.0.0", 9001, "192.168.1.20"),
            "http://192.168.1.20:9001/certificado",
        )
        self.assertEqual(
            certificate_portal_url("localhost", 8001, "192.168.1.20"),
            "http://localhost:8001/certificado",
        )

    def test_printer_route_identifies_matching_local_bridge(self):
        self.assertEqual(
            printer_route_label("127.0.0.1", 9100, True, 9100),
            "Puente USB local",
        )
        self.assertEqual(
            printer_route_label("127.0.0.1", 9100, False, 9100),
            "Ruta local; habilita el puente USB",
        )
        self.assertEqual(
            printer_route_label("192.168.1.50", 9100, True, 9100),
            "Impresora de red",
        )

    def test_tooltip_moves_left_and_stays_inside_screen(self):
        self.assertEqual(
            tooltip_coordinates(980, 740, 24, 300, 100, 1024, 768),
            (672, 660),
        )


if __name__ == "__main__":
    unittest.main()
