import unittest

from PIL import Image

from moviu_server.resources import APP_ICON_ICO_PATH, APP_ICON_PATH, load_app_icon


class AppIconTests(unittest.TestCase):
    def test_icon_assets_are_valid_images(self):
        self.assertTrue(APP_ICON_PATH.is_file())
        self.assertTrue(APP_ICON_ICO_PATH.is_file())

        with Image.open(APP_ICON_PATH) as png_icon:
            self.assertEqual(png_icon.format, "PNG")
        with Image.open(APP_ICON_ICO_PATH) as windows_icon:
            self.assertEqual(windows_icon.format, "ICO")

    def test_load_app_icon_trims_transparent_margin(self):
        with Image.open(APP_ICON_PATH) as source:
            source_size = source.size

        icon = load_app_icon()

        self.assertEqual(icon.mode, "RGBA")
        self.assertLess(icon.width, source_size[0])
        self.assertLess(icon.height, source_size[1])
        self.assertEqual(icon.getbbox(), (0, 0, icon.width, icon.height))

    def test_load_app_icon_centers_it_on_requested_canvas(self):
        icon = load_app_icon(64)

        self.assertEqual(icon.size, (64, 64))
        self.assertEqual(icon.mode, "RGBA")
        left, top, right, bottom = icon.getbbox()
        self.assertLessEqual(abs(left - (64 - right)), 1)
        self.assertLessEqual(abs(top - (64 - bottom)), 1)

    def test_load_app_icon_rejects_invalid_size(self):
        with self.assertRaises(ValueError):
            load_app_icon(0)


if __name__ == "__main__":
    unittest.main()
