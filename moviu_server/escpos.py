"""Minimal helpers for ESC/POS encoding."""

from __future__ import annotations

import math
from typing import Iterable

from PIL import Image


def image_to_escpos(image: Image.Image, cut: bool = True, chunk_height: int = 128, gamma: float = 1.0) -> bytes:
    """Convert a Pillow image into ESC/POS raster bytes using intelligent chunking."""

    # Handle transparency: composite onto a white background to avoid black blobs
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        grayscale = background.convert("L")
    else:
        grayscale = image.convert("L")

    # Apply gamma correction if needed
    if gamma != 1.0:
        # O = 255 * (I/255)^(1/gamma)
        inv_gamma = 1.0 / gamma
        lut = [pow(i / 255.0, inv_gamma) * 255.0 for i in range(256)]
        grayscale = grayscale.point(lut)

    bw = grayscale.point(lambda x: 0 if x < 128 else 255, "1")
    width = bw.width
    height = bw.height
    width_bytes = math.ceil(width / 8)
    pixels = bw.load()

    payload = bytearray()
    payload.extend(b"\x1b@")  # Initialize printer

    # Split image into chunks to avoid printer buffer overflow
    for y_start in range(0, height, chunk_height):
        current_chunk_height = min(chunk_height, height - y_start)
        
        # GS v 0 m xL xH yL yH
        payload.extend(b"\x1dv0\x00")  # Mode 0 (Normal)
        payload.extend(bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF]))
        payload.extend(bytes([current_chunk_height & 0xFF, (current_chunk_height >> 8) & 0xFF]))

        for y in range(y_start, y_start + current_chunk_height):
            for x_byte in range(width_bytes):
                byte = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width:
                        pixel = pixels[x, y]
                        if pixel == 0:
                            byte |= 1 << (7 - bit)
                payload.append(byte)
    
    if cut:
        payload.extend(b"\n\n\x1dV0")  # Feed and cut
    
    return bytes(payload)


def ensure_bytes(data: Iterable[int] | bytes | bytearray | str) -> bytes:
    """Normalize different payload representations into bytes."""

    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("latin-1", errors="ignore")
    return bytes(data)
