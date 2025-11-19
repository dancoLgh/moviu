"""Printer orchestration for the local API."""

from __future__ import annotations

import base64
import io
import socket
from dataclasses import dataclass
from typing import Literal, Optional

from PIL import Image

from .escpos import image_to_escpos
from .html_renderer import html_to_image


@dataclass
class PrintJob:
    mode: Literal["html", "image", "raw", "raw_text"]
    content: str
    printer_host: str
    printer_port: int
    auto_cut: bool = True


class PrinterError(RuntimeError):
    """Domain-specific errors for job processing."""


class PrintProcessor:
    """Handle conversions and network transmission."""

    def __init__(self, default_host: str, default_port: int) -> None:
        self.default_host = default_host
        self.default_port = default_port

    def process(self, job: PrintJob) -> dict:
        payload = self._build_payload(job)
        self._send_to_printer(payload, job.printer_host, job.printer_port)
        return {
            "status": "sent",
            "host": job.printer_host,
            "port": job.printer_port,
            "bytes": len(payload),
        }

    def _build_payload(self, job: PrintJob) -> bytes:
        if job.mode == "raw_text":
            return job.content.encode("latin-1")
        if job.mode == "raw":
            return self._decode_raw(job.content)
        if job.mode == "image":
            image = self._decode_image(job.content)
        elif job.mode == "html":
            image = html_to_image(job.content)
        else:
            raise PrinterError(f"Modo no soportado: {job.mode}")
        return image_to_escpos(image)

    @staticmethod
    def _decode_raw(content: str) -> bytes:
        """Decode transport-friendly strings (hex/base64) into bytes."""

        data = content.strip()
        try:
            return bytes.fromhex(data)
        except ValueError:
            pass
        try:
            return base64.b64decode(data)
        except Exception as exc:  # noqa: BLE001
            raise PrinterError(
                "El contenido raw debe ser una cadena hexadecimal o base64"
            ) from exc

    @staticmethod
    def _decode_image(data: str) -> Image.Image:
        try:
            if data.startswith("data:image"):
                _, b64_data = data.split(",", 1)
                raw = base64.b64decode(b64_data)
            else:
                raw = base64.b64decode(data)
        except Exception as exc:  # noqa: BLE001
            raise PrinterError("La imagen debe estar codificada en base64") from exc
        return Image.open(io.BytesIO(raw))

    @staticmethod
    def _send_to_printer(payload: bytes, host: Optional[str], port: Optional[int]) -> None:
        target_host = host or "127.0.0.1"
        target_port = port or 9100
        try:
            with socket.create_connection((target_host, target_port), timeout=10) as sock:
                sock.sendall(payload)
        except OSError as exc:
            raise PrinterError(
                f"No se pudo enviar el trabajo a {target_host}:{target_port}: {exc}"
            ) from exc
