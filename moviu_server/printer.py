"""Printer orchestration for the local API."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
import socket
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Literal, Optional
from uuid import uuid4

from PIL import Image

from .config import CONFIG_DIR
from .escpos import image_to_escpos
from .html_renderer import html_to_image
from .system_printer import SystemPrinterError, print_raw_to_system_printer


@dataclass
class PrintJob:
    mode: Literal["html", "image", "pdf", "raw", "raw_text", "zpl", "hybrid"]
    content: str
    printer_host: str
    printer_port: int
    printer_name: Optional[str] = None
    auto_cut: bool = True
    code_page: Optional[str] = None
    gamma: Optional[int] = None


class PrinterError(RuntimeError):
    """Domain-specific errors for job processing."""


_SEND_LOCKS: dict[tuple[str, int], threading.Lock] = {}
_SEND_LOCKS_GUARD = threading.Lock()


def _get_send_lock(host: str, port: int) -> threading.Lock:
    key = (host, port)
    with _SEND_LOCKS_GUARD:
        lock = _SEND_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _SEND_LOCKS[key] = lock
        return lock


class PrintProcessor:
    """Handle conversions and network transmission."""

    def __init__(
        self,
        default_host: str,
        default_port: int,
        width: int = 576,
        gamma: int = 500,
        simulate: bool = False,
    ) -> None:
        self.default_host = default_host
        self.default_port = default_port
        self.width = width
        self.gamma_config = gamma
        self.simulate = simulate

    def _get_actual_gamma(self, user_gamma: Optional[int]) -> float:
        """Convert user-friendly range (200-1000) to actual log-gamma (10.0-0.01).
        
        Neutral (500) is now shifted to be slightly darker (0.5 gamma)
        to satisfy the request for darker prints.
        1000 is extremely aggressive (approx 0.001 gamma).
        """
        val = user_gamma if user_gamma is not None else self.gamma_config
        # Center shifted to 350 to make 500 have a gamma of ~0.25 (quite dark)
        # And 1000 have a gamma of ~10^-2.6 (practically black)
        return float(10 ** ((350 - val) / 250))

    def process(self, job: PrintJob, simulate_override: Optional[bool] = None) -> dict:
        payload, preview = self._build_payload(job)
        simulate = self.simulate if simulate_override is None else simulate_override
        preview_data: dict | None = None

        payload_size = len(payload)
        payload_hash = hashlib.sha256(payload).hexdigest()[:16]
        job_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:8]
        target_printer = job.printer_name
        target_host = job.printer_host or self.default_host
        target_port = job.printer_port or self.default_port

        if target_printer:
            logging.info(
                "Job %s prepared (mode=%s printer=%s bytes=%d sha256=%s)",
                job_id,
                job.mode,
                target_printer,
                payload_size,
                payload_hash,
            )
        else:
            logging.info(
                "Job %s prepared (mode=%s host=%s port=%s bytes=%d sha256=%s)",
                job_id,
                job.mode,
                target_host,
                target_port,
                payload_size,
                payload_hash,
            )

        if simulate:
            preview_data = self._simulate_output(job, payload, preview, job_id, payload_hash)
            status = "simulated"
            local_result: dict[str, object] | None = None
        else:
            local_result = None
            if target_printer:
                try:
                    local_result = print_raw_to_system_printer(
                        payload,
                        target_printer,
                        document_name=f"Moviu {job.mode.upper()} Print",
                    )
                except SystemPrinterError as exc:
                    raise PrinterError(str(exc)) from exc
                status = str(local_result.get("status", "sent"))
            else:
                self._send_to_printer(payload, target_host, target_port, job_id=job_id)
                status = "sent"

        response = {
            "status": status,
            "job_id": job_id,
            "bytes": payload_size,
        }
        if target_printer:
            response["printer"] = target_printer
            if local_result and "message" in local_result:
                response["message"] = local_result["message"]
        else:
            response["host"] = target_host
            response["port"] = target_port
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
            payload, zpl_preview = self._decode_zpl(job.content, job.code_page)
            preview = {"zpl": zpl_preview, "encoding": (job.code_page or "latin-1").lower()}
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
                
                gamma = self._get_actual_gamma(job.gamma)
                image_payload = image_to_escpos(image, cut=False, gamma=gamma)
                
                # Process commands
                commands_payload = self._decode_raw(commands_data)
                
                preview = {"image": image, "commands_hex": commands_payload.hex()}
                return image_payload + commands_payload, preview
            except json.JSONDecodeError as exc:
                raise PrinterError(f"Contenido hybrid inválido (debe ser JSON): {exc}") from exc
        else:
            raise PrinterError(f"Modo no soportado: {job.mode}")
        
        gamma = self._get_actual_gamma(job.gamma)
        return image_to_escpos(image, gamma=gamma), preview

    @staticmethod
    def _decode_raw(content: str) -> bytes:
        """Decode transport-friendly strings (hex/base64) into bytes."""

        data = re.sub(r"\s+", "", content.strip())
        try:
            return bytes.fromhex(data)
        except ValueError:
            pass
        try:
            return base64.b64decode(data, validate=True)
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
    def _decode_zpl(content: str, code_page: Optional[str] = None) -> tuple[bytes, str]:
        r"""Decode ZPL text preserving Zebra-friendly single-byte encodings."""

        encoding = (code_page or "latin-1").lower()
        try:
            text = content.strip()

            if "^XA" not in text and "^XZ" not in text:
                compact = re.sub(r"\s+", "", text)
                try:
                    decoded = base64.b64decode(compact, validate=True)
                    text = decoded.decode(encoding)
                except Exception:
                    text = content.strip()

            text = text.replace("\\n", "\n").replace("\\r", "\r")

            def _hex_repl(match: re.Match) -> str:
                value = int(match.group(1), 16)
                return chr(value)

            text = re.sub(r"\\x([0-9A-Fa-f]{2})", _hex_repl, text)

            if "^XA" not in text and "~JA" not in text and "^XZ" not in text:
                raise PrinterError("El contenido ZPL no parece válido: falta ^XA/^XZ")

            if "^XZ" in text and not text.endswith(("\n", "\r")):
                text += "\n"

            payload = text.encode(encoding, errors="strict")
            return payload, text
        except LookupError as exc:
            raise PrinterError(f"Code page no soportada para zpl: {encoding}") from exc
        except UnicodeEncodeError as exc:
            raise PrinterError(
                f"El ZPL contiene caracteres no soportados por la codificación {encoding}"
            ) from exc

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
                raw = base64.b64decode(re.sub(r"\s+", "", b64_data), validate=True)
            else:
                stripped = re.sub(r"\s+", "", data.strip())
                try:
                    # Try hex first as it's more specific
                    raw = bytes.fromhex(stripped)
                except ValueError:
                    raw = base64.b64decode(stripped, validate=True)
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
                raw = base64.b64decode(re.sub(r"\s+", "", b64_data), validate=True)
            else:
                raw = base64.b64decode(re.sub(r"\s+", "", data), validate=True)
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
    def _send_to_printer(
        payload: bytes,
        host: Optional[str],
        port: Optional[int],
        *,
        job_id: Optional[str] = None,
    ) -> None:
        target_host = host or "127.0.0.1"
        target_port = port or 9100
        payload_size = len(payload)
        send_lock = _get_send_lock(target_host, target_port)

        try:
            with send_lock:
                with socket.create_connection((target_host, target_port), timeout=10) as sock:
                    total_sent = 0
                    view = memoryview(payload)

                    # Use smaller chunks to improve compatibility with low-buffer printers.
                    chunk_size = 4096
                    while total_sent < payload_size:
                        sent = sock.send(view[total_sent : total_sent + chunk_size])
                        if sent <= 0:
                            raise PrinterError(
                                f"Socket send devolvio {sent} en offset {total_sent}/{payload_size}"
                            )
                        total_sent += sent

                        # Tiny pacing to avoid overrun on some ESC/POS network adapters.
                        if total_sent < payload_size:
                            time.sleep(0.002)
        except OSError as exc:
            raise PrinterError(
                f"No se pudo enviar el trabajo a {target_host}:{target_port}: {exc}"
            ) from exc

        logging.info(
            "Job %s sent to %s:%s (%d bytes)",
            job_id or "-",
            target_host,
            target_port,
            payload_size,
        )

    def _simulate_output(
        self,
        job: PrintJob,
        payload: bytes,
        preview: dict,
        job_id: str,
        payload_hash: str,
    ) -> dict:
        jobs_dir = CONFIG_DIR / "simulated_jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        safe_job_id = job_id.replace(":", "-")
        base = jobs_dir / f"job-{safe_job_id}"

        payload_path = base.with_suffix(".bin")
        payload_path.write_bytes(payload)

        summary_lines = [
            f"Job: {job_id}",
            f"Modo: {job.mode}",
            f"Bytes: {len(payload)}",
            f"sha256: {payload_hash}",
        ]

        inline_preview: dict = {
            "job_id": job_id,
            "payload_sha256": payload_hash,
            "payload_path": str(payload_path),
        }

        if job.printer_name:
            summary_lines.append(f"Impresora: {job.printer_name}")
            inline_preview["printer"] = job.printer_name
        else:
            summary_lines.append(f"Host: {job.printer_host or self.default_host}")
            summary_lines.append(f"Puerto: {job.printer_port or self.default_port}")
            inline_preview["host"] = job.printer_host or self.default_host
            inline_preview["port"] = job.printer_port or self.default_port

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
                summary_lines.append(f"Previsualizacion: {image_path}")
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
