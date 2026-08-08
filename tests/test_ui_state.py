import unittest

from moviu_server.ui_state import ActivityFeed, NAV_ITEMS


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
            ["home", "printers", "connection", "activity", "settings"],
        )


if __name__ == "__main__":
    unittest.main()
