"""Printer orchestration for the local API."""

from __future__ import annotations

import base64
import io
import json
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
    mode: Literal["html", "image", "pdf", "raw", "raw_text", "zpl", "hybrid"]
    content: str
    printer_host: str
    printer_port: int
    auto_cut: bool = True
    code_page: Optional[str] = None


class PrinterError(RuntimeError):
    """Domain-specific errors for job processing."""


class PrintProcessor:
    """Handle conversions and network transmission."""

    def __init__(self, default_host: str, default_port: int, width: int = 576, simulate: bool = False) -> None:
        self.default_host = default_host
        self.default_port = default_port
        self.width = width
        self.simulate = simulate

    def process(self, job: PrintJob, simulate_override: Optional[bool] = None) -> dict:
        payload, preview = self._build_payload(job)
        simulate = self.simulate if simulate_override is None else simulate_override
        preview_data: dict | None = None

        if simulate:
            preview_data = self._simulate_output(job, payload, preview)
            status = "simulated"
        else:
            self._send_to_printer(payload, job.printer_host, job.printer_port)
            status = "sent"

        response = {
            "status": status,
            "host": job.printer_host,
            "port": job.printer_port,
            "bytes": len(payload),
        }
        if preview_data:
            response["preview"] = preview_data
        return response

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
        if job.mode == "zpl":
            payload = job.content.encode("utf-8")
            preview = {"zpl": job.content}
            return payload, preview
        if job.mode == "image":
            image = self._decode_image(job.content)
            # Resize if needed to fit printer width
            if image.width > self.width:
                ratio = self.width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((self.width, new_height), Image.Resampling.LANCZOS)
            preview = {"image": image}
        elif job.mode == "html":
            image = html_to_image(job.content, width=self.width)
            preview = {"image": image, "html": job.content}
        elif job.mode == "pdf":
            image = self._decode_pdf(job.content)
            preview = {"image": image}
        elif job.mode == "hybrid":
            # Hybrid mode: content is JSON with {image: "...", commands: "..."}
            try:
                data = json.loads(job.content)
                image_data = data.get("image")
                commands_data = data.get("commands")

                if not image_data or not commands_data:
                    raise PrinterError("Modo hybrid requiere 'image' y 'commands' en el JSON")

                # Process image (no cut)
                image = self._decode_image(image_data)
                if image.width > self.width:
                    ratio = self.width / image.width
                    new_height = int(image.height * ratio)
                    image = image.resize((self.width, new_height), Image.Resampling.LANCZOS)
                
                image_payload = image_to_escpos(image, cut=False)
                
                # Process commands
                commands_payload = self._decode_raw(commands_data)
                
                preview = {"image": image, "commands_hex": commands_payload.hex()}
                return image_payload + commands_payload, preview
            except json.JSONDecodeError as exc:
                raise PrinterError(f"Contenido hybrid inválido (debe ser JSON): {exc}") from exc
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
                stripped = data.strip()
                try:
                    # Try hex first as it's more specific
                    raw = bytes.fromhex(stripped)
                except ValueError:
                    raw = base64.b64decode(stripped)
        except Exception as exc:  # noqa: BLE001
            raise PrinterError("La imagen debe estar codificada en base64 o hexadecimal") from exc
        return Image.open(io.BytesIO(raw))

    def _decode_pdf(self, data: str) -> Image.Image:
        """Convert a base64-encoded PDF to a single concatenated image.

        Each page is rendered and all pages are stacked vertically.
        The result is resized to fit the printer width.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise PrinterError(
                "PyMuPDF no está instalado. Ejecuta: pip install pymupdf"
            ) from exc

        try:
            if data.startswith("data:application/pdf"):
                _, b64_data = data.split(",", 1)
                raw = base64.b64decode(b64_data)
            else:
                raw = base64.b64decode(data)
        except Exception as exc:  # noqa: BLE001
            raise PrinterError("El PDF debe estar codificado en base64") from exc

        try:
            doc = fitz.open(stream=raw, filetype="pdf")
        except Exception as exc:  # noqa: BLE001
            raise PrinterError(f"No se pudo abrir el PDF: {exc}") from exc

        if doc.page_count == 0:
            raise PrinterError("El PDF no tiene páginas")

        images: list[Image.Image] = []
        # Calculate zoom to fit printer width (72 DPI base)
        zoom = self.width / 595.0  # A4 width in points ≈ 595
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            images.append(img)

        doc.close()

        # Concatenate all pages vertically
        total_height = sum(img.height for img in images)
        final_width = max(img.width for img in images)
        combined = Image.new("L", (final_width, total_height), 255)

        y_offset = 0
        for img in images:
            combined.paste(img, (0, y_offset))
            y_offset += img.height

        # Resize if needed to fit printer width
        if combined.width > self.width:
            ratio = self.width / combined.width
            new_height = int(combined.height * ratio)
            combined = combined.resize((self.width, new_height), Image.Resampling.LANCZOS)

        return combined

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

    def _simulate_output(self, job: PrintJob, payload: bytes, preview: dict) -> dict:
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

        inline_preview: dict = {
            "host": job.printer_host or self.default_host,
            "port": job.printer_port or self.default_port,
            "payload_path": str(payload_path),
        }

        if "text" in preview:
            text_path = base.with_suffix(".txt")
            text_path.write_text(preview["text"], encoding="utf-8")
            summary_lines.append(f"Vista previa texto: {text_path}")
            inline_preview["text"] = preview["text"]
        if "hex" in preview:
            hex_path = base.with_suffix(".hex")
            hex_path.write_text(preview["hex"], encoding="utf-8")
            summary_lines.append(f"Hex dump: {hex_path}")
            inline_preview["hex"] = preview["hex"]
        if "html" in preview:
            html_path = base.with_suffix(".html")
            html_path.write_text(preview["html"], encoding="utf-8")
            summary_lines.append(f"HTML recibido: {html_path}")
            inline_preview["html"] = preview["html"]
        if "image" in preview:
            image_path = base.with_suffix(".png")
            try:
                preview["image"].save(image_path)
                summary_lines.append(f"Previsualización: {image_path}")
                buffer = io.BytesIO()
                preview["image"].save(buffer, format="PNG")
                inline_preview["image_base64"] = base64.b64encode(buffer.getvalue()).decode(
                    "ascii"
                )
            except Exception as exc:  # noqa: BLE001
                logging.warning("No se pudo guardar la vista previa de imagen: %s", exc)
        summary = " | ".join(summary_lines)
        logging.info("Trabajo simulado guardado en %s (%s)", payload_path, summary)
        return inline_preview
