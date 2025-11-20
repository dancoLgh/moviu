"""Printer orchestration for the local API."""

from __future__ import annotations

import base64
import io
import logging
import re
import socket
from datetime import datetime
from dataclasses import dataclass
from typing import Literal, Optional

from PIL import Image

from .config import CONFIG_DIR
from .escpos import image_to_escpos
from .html_renderer import html_to_image


@dataclass
class PrintJob:
    mode: Literal["html", "image", "raw", "raw_text"]
    content: str
    printer_host: str
    printer_port: int
    auto_cut: bool = True
    code_page: Optional[str] = None


class PrinterError(RuntimeError):
    """Domain-specific errors for job processing."""


class PrintProcessor:
    """Handle conversions and network transmission."""

    def __init__(self, default_host: str, default_port: int, simulate: bool = False) -> None:
        self.default_host = default_host
        self.default_port = default_port
        self.simulate = simulate

    def process(self, job: PrintJob) -> dict:
        payload, preview = self._build_payload(job)
        if self.simulate:
            self._simulate_output(job, payload, preview)
            status = "simulated"
        else:
            self._send_to_printer(payload, job.printer_host, job.printer_port)
            status = "sent"
        return {
            "status": status,
            "host": job.printer_host,
            "port": job.printer_port,
            "bytes": len(payload),
        }

    def _build_payload(self, job: PrintJob) -> tuple[bytes, dict]:
        preview: dict = {}
        if job.mode == "raw_text":
            payload, text_preview = self._decode_raw_text(job.content, job.code_page)
            preview = {"text": text_preview, "encoding": (job.code_page or "cp858").lower()}
            return payload, preview
        if job.mode == "raw":
            payload = self._decode_raw(job.content)
            preview = {"hex": payload.hex()}
            return payload, preview
        if job.mode == "image":
            image = self._decode_image(job.content)
            preview = {"image": image}
        elif job.mode == "html":
            image = html_to_image(job.content)
            preview = {"image": image, "html": job.content}
        else:
            raise PrinterError(f"Modo no soportado: {job.mode}")
        return image_to_escpos(image), preview

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
    def _decode_raw_text(content: str, code_page: Optional[str] = None) -> tuple[bytes, str]:
        r"""Decode \xNN escapes + newlines without mangling accented characters."""

        encoding = (code_page or "cp858").lower()
        try:
            text = content

            # 1) Turn literal "\n"/"\r" into real control characters
            text = text.replace("\\n", "\n").replace("\\r", "\r")

            # 2) Replace \xHH escape sequences with their character equivalents
            def _hex_repl(match: re.Match) -> str:
                value = int(match.group(1), 16)
                return chr(value)

            text = re.sub(r"\\x([0-9A-Fa-f]{2})", _hex_repl, text)

            # 3) Encode everything using the printer's code page
            payload = text.encode(encoding, errors="replace")

            # 4) Prefix ESC t n to set the printer code page
            prefix = PrintProcessor._code_page_command(encoding)
            return (prefix + payload if prefix else payload), text
        except LookupError as exc:  # Unknown codec
            raise PrinterError(f"Code page no soportada: {encoding}") from exc
        except Exception as exc:  # noqa: BLE001
            raise PrinterError("No se pudo decodificar raw_text") from exc

    @staticmethod
    def _code_page_command(encoding: str) -> bytes:
        """Return the ESC t n sequence for common code pages if known.

        The indexes match the typical ESC/POS tables shown by most thermal
        printers (0=PC437, 2=PC850, 6=Windows-1252, 8=PC852, 9=PC858, etc.).
        """

        mapping = {
            "cp437": 0,
            "437": 0,
            "cp850": 2,
            "850": 2,
            "cp860": 3,
            "860": 3,
            "cp863": 4,
            "863": 4,
            "cp865": 5,
            "865": 5,
            "cp1252": 6,
            "windows-1252": 6,
            "latin-1": 6,
            "iso-8859-1": 6,
            "cp866": 7,
            "866": 7,
            "cp852": 8,
            "852": 8,
            "cp858": 9,
            "858": 9,
        }
        if encoding not in mapping:
            return b""
        return bytes([0x1B, 0x74, mapping[encoding]])

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

    def _simulate_output(self, job: PrintJob, payload: bytes, preview: dict) -> None:
        jobs_dir = CONFIG_DIR / "simulated_jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = jobs_dir / f"job-{timestamp}"

        payload_path = base.with_suffix(".bin")
        payload_path.write_bytes(payload)

        summary_lines = [
            f"Modo: {job.mode}",
            f"Host: {job.printer_host or self.default_host}",
            f"Puerto: {job.printer_port or self.default_port}",
            f"Bytes: {len(payload)}",
        ]

        if "text" in preview:
            text_path = base.with_suffix(".txt")
            text_path.write_text(preview["text"], encoding="utf-8")
            summary_lines.append(f"Vista previa texto: {text_path}")
        if "hex" in preview:
            hex_path = base.with_suffix(".hex")
            hex_path.write_text(preview["hex"], encoding="utf-8")
            summary_lines.append(f"Hex dump: {hex_path}")
        if "html" in preview:
            html_path = base.with_suffix(".html")
            html_path.write_text(preview["html"], encoding="utf-8")
            summary_lines.append(f"HTML recibido: {html_path}")
        if "image" in preview:
            image_path = base.with_suffix(".png")
            try:
                preview["image"].save(image_path)
                summary_lines.append(f"Previsualización: {image_path}")
            except Exception as exc:  # noqa: BLE001
                logging.warning("No se pudo guardar la vista previa de imagen: %s", exc)
        summary = " | ".join(summary_lines)
        logging.info("Trabajo simulado guardado en %s (%s)", payload_path, summary)
