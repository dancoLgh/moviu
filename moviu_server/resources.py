"""Packaged visual resources for the desktop application."""

from pathlib import Path

from PIL import Image


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
APP_ICON_PATH = ASSETS_DIR / "moviu-isotipo.png"
APP_ICON_ICO_PATH = ASSETS_DIR / "moviu-isotipo.ico"


def load_app_icon(size: int | None = None) -> Image.Image:
    """Load the Moviu logo, removing transparent margins when resizing it."""
    if size is not None and size <= 0:
        raise ValueError("Icon size must be greater than zero")

    with Image.open(APP_ICON_PATH) as source:
        image = source.convert("RGBA")

    bounds = image.getbbox()
    if bounds:
        image = image.crop(bounds)

    if size is None:
        return image

    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    position = ((size - image.width) // 2, (size - image.height) // 2)
    canvas.alpha_composite(image, position)
    return canvas
