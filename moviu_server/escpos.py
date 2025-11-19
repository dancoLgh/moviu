"""Minimal helpers for ESC/POS encoding."""

from __future__ import annotations

import math
from typing import Iterable

from PIL import Image


def image_to_escpos(image: Image.Image) -> bytes:
    """Convert a Pillow image into ESC/POS raster bytes."""

    grayscale = image.convert("L")
    bw = grayscale.point(lambda x: 0 if x < 128 else 255, "1")
    width = bw.width
    height = bw.height
    width_bytes = math.ceil(width / 8)

    header = bytearray()
    header.extend(b"\x1b@")  # Initialize printer
    header.extend(b"\x1dv0")  # Select bit image mode
    header.append(0)  # m = 0 (normal density)
    header.extend((width_bytes & 0xFF, (width_bytes >> 8) & 0xFF))
    header.extend((height & 0xFF, (height >> 8) & 0xFF))

    body = bytearray()
    pixels = bw.load()
    for y in range(height):
        for x_byte in range(width_bytes):
            byte = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < width:
                    pixel = pixels[x, y]
                    if pixel == 0:
                        byte |= 1 << (7 - bit)
            body.append(byte)
    body.extend(b"\n\n\x1dV0")  # Feed and cut
    return bytes(header + body)


def ensure_bytes(data: Iterable[int] | bytes | bytearray | str) -> bytes:
    """Normalize different payload representations into bytes."""

    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("latin-1", errors="ignore")
    return bytes(data)
