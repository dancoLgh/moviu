"""System printer support for standard printers (laser, inkjet, etc.)."""

from __future__ import annotations

import io
import logging
import platform
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

if platform.system() == "Windows":
    import win32print  # type: ignore
    import win32ui  # type: ignore
    import win32con  # type: ignore
    from PIL import ImageWin  # type: ignore
else:
    win32print = None  # type: ignore
    win32ui = None  # type: ignore
    win32con = None  # type: ignore
    ImageWin = None  # type: ignore


class SystemPrinterError(RuntimeError):
    """Errors related to system printing."""


_PAPER_SIZE_CONSTANT_BY_ALIAS = {
    "a3": "DMPAPER_A3",
    "a4": "DMPAPER_A4",
    "a5": "DMPAPER_A5",
    "a6": "DMPAPER_A6",
    "letter": "DMPAPER_LETTER",
    "carta": "DMPAPER_LETTER",
    "legal": "DMPAPER_LEGAL",
    "oficio": "DMPAPER_LEGAL",
    "tabloid": "DMPAPER_TABLOID",
    "ledger": "DMPAPER_LEDGER",
    "statement": "DMPAPER_STATEMENT",
    "executive": "DMPAPER_EXECUTIVE",
    "b4": "DMPAPER_B4",
    "b5": "DMPAPER_B5",
}


def _resolve_paper_size_code(paper_size: str) -> int:
    """Resolve user-provided paper size into a Windows DMPAPER code."""
    normalized = (
        paper_size.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    )
    if not normalized:
        raise SystemPrinterError("paper_size no puede estar vacío")

    if normalized.isdigit():
        code = int(normalized)
        if code <= 0:
            raise SystemPrinterError("paper_size numérico debe ser mayor a 0")
        return code

    constant_name = _PAPER_SIZE_CONSTANT_BY_ALIAS.get(normalized)
    if not constant_name:
        supported = "A3, A4, A5, A6, Letter, Legal, Tabloid, Ledger, Statement, Executive, B4, B5"
        raise SystemPrinterError(
            f"paper_size '{paper_size}' no soportado. Usa {supported} o un código DMPAPER numérico."
        )

    if win32con is None:
        raise SystemPrinterError("paper_size solo está disponible en Windows")

    code = getattr(win32con, constant_name, None)
    if code is None:
        raise SystemPrinterError(
            f"El sistema no expone la constante {constant_name} para paper_size='{paper_size}'"
        )
    return int(code)


def _resolve_custom_paper_size_tenths_mm(width_mm: float, height_mm: float) -> tuple[int, int]:
    """Convert custom size in millimeters to tenths of millimeter for DEVMODE."""
    width_tenths = int(round(width_mm * 10.0))
    height_tenths = int(round(height_mm * 10.0))

    if width_tenths <= 0 or height_tenths <= 0:
        raise SystemPrinterError("paper_width_mm y paper_height_mm deben ser mayores a 0")

    # DEVMODE uses 16-bit signed values for PaperWidth/PaperLength.
    max_tenths = 32767
    if width_tenths > max_tenths or height_tenths > max_tenths:
        raise SystemPrinterError(
            "paper_width_mm/paper_height_mm exceden el máximo permitido por Windows (3276.7 mm)"
        )

    return width_tenths, height_tenths


def _render_pdf_to_images(pdf_data: bytes, dpi: int = 150) -> list:
    """Render PDF pages to PIL Images using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise SystemPrinterError(
            "PyMuPDF no está instalado. Ejecuta: pip install pymupdf"
        ) from exc

    from PIL import Image

    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
    except Exception as exc:
        raise SystemPrinterError(f"No se pudo abrir el PDF: {exc}") from exc

    if doc.page_count == 0:
        raise SystemPrinterError("El PDF no tiene páginas")

    images = []
    zoom = dpi / 72.0  # 72 is the base DPI for PDF
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(img)

    doc.close()
    return images


def print_pdf_to_system_printer(
    pdf_data: bytes,
    printer_name: Optional[str] = None,
    dpi: int = 150,
    paper_size: Optional[str] = None,
    paper_width_mm: Optional[float] = None,
    paper_height_mm: Optional[float] = None,
) -> dict:
    """Print a PDF to a system printer (laser, inkjet, etc.).

    Renders the PDF to images and prints each page using Windows GDI.

    Args:
        pdf_data: Raw PDF bytes.
        printer_name: Name of the printer. If None, uses default printer.
        dpi: Resolution for rendering (default 150 for good quality/speed balance).
        paper_size: Paper size alias (A4, Letter, Legal, etc.) or numeric DMPAPER code.
        paper_width_mm: Custom paper width in mm (must be sent with paper_height_mm).
        paper_height_mm: Custom paper height in mm (must be sent with paper_width_mm).

    Returns:
        dict with status and details.
    """
    has_custom_width = paper_width_mm is not None
    has_custom_height = paper_height_mm is not None
    if has_custom_width != has_custom_height:
        raise SystemPrinterError(
            "Para tamaño personalizado debes enviar paper_width_mm y paper_height_mm juntos"
        )
    if paper_size is not None and has_custom_width:
        raise SystemPrinterError(
            "No combines paper_size con paper_width_mm/paper_height_mm; usa solo una opción"
        )

    if platform.system() != "Windows":
        # For non-Windows, save to temp and log
        out_dir = Path.home() / ".moviu_printer" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "system_print_job.pdf"
        job_path.write_bytes(pdf_data)
        logger.info("Sistema no Windows: PDF guardado en %s", job_path)
        result: dict[str, object] = {
            "status": "simulated",
            "message": f"PDF guardado en {job_path} (no Windows)",
            "printer": "none",
        }
        if paper_size is not None:
            result["paper_size"] = paper_size
        if has_custom_width and has_custom_height:
            result["paper_width_mm"] = paper_width_mm
            result["paper_height_mm"] = paper_height_mm
        return result

    if win32print is None or win32ui is None:
        raise SystemPrinterError("win32print/win32ui no disponible")
    assert win32print is not None
    assert win32ui is not None
    assert win32con is not None
    assert ImageWin is not None

    # Get printer name
    if printer_name:
        target_printer = printer_name
    else:
        target_printer = win32print.GetDefaultPrinter()

    if not target_printer:
        raise SystemPrinterError("No hay impresora predeterminada configurada")

    # Render PDF to images
    images = _render_pdf_to_images(pdf_data, dpi=dpi)

    paper_size_code: Optional[int] = None
    custom_paper_width_tenths: Optional[int] = None
    custom_paper_height_tenths: Optional[int] = None
    if paper_size:
        paper_size_code = _resolve_paper_size_code(paper_size)
    elif has_custom_width and has_custom_height:
        assert paper_width_mm is not None
        assert paper_height_mm is not None
        custom_paper_width_tenths, custom_paper_height_tenths = _resolve_custom_paper_size_tenths_mm(
            paper_width_mm,
            paper_height_mm,
        )

    try:
        # Create device context for printer
        hdc = win32ui.CreateDC()
        if hdc is None:
            raise SystemPrinterError("No se pudo crear el contexto de dispositivo de la impresora")
        hdc.CreatePrinterDC(target_printer)

        if paper_size_code is not None or (
            custom_paper_width_tenths is not None and custom_paper_height_tenths is not None
        ):
            handle = win32print.OpenPrinter(target_printer)
            try:
                printer_info = win32print.GetPrinter(handle, 2)
                devmode = printer_info.get("pDevMode")
                if devmode is None:
                    raise SystemPrinterError("No se pudo leer la configuración de impresión (DEVMODE)")

                if paper_size_code is not None:
                    devmode.PaperSize = paper_size_code
                    if hasattr(win32con, "DM_PAPERSIZE"):
                        devmode.Fields |= win32con.DM_PAPERSIZE
                else:
                    if not hasattr(win32con, "DM_PAPERWIDTH") or not hasattr(win32con, "DM_PAPERLENGTH"):
                        raise SystemPrinterError(
                            "El sistema no soporta ajuste de tamaño personalizado (DM_PAPERWIDTH/DM_PAPERLENGTH)"
                        )
                    assert custom_paper_width_tenths is not None
                    assert custom_paper_height_tenths is not None
                    devmode.PaperSize = 0
                    devmode.PaperWidth = custom_paper_width_tenths
                    devmode.PaperLength = custom_paper_height_tenths
                    devmode.Fields |= win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH

                hdc.ResetDC(devmode)
            finally:
                win32print.ClosePrinter(handle)

            if paper_size_code is not None:
                logger.info(
                    "Tamaño de hoja solicitado para %s: %s (código %d)",
                    target_printer,
                    paper_size,
                    paper_size_code,
                )
            else:
                logger.info(
                    "Tamaño de hoja personalizado para %s: %.2fmm x %.2fmm",
                    target_printer,
                    paper_width_mm,
                    paper_height_mm,
                )

        # Get printer capabilities
        printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
        printable_height = hdc.GetDeviceCaps(win32con.VERTRES)

        hdc.StartDoc("Moviu PDF Print")

        for page_num, img in enumerate(images):
            hdc.StartPage()

            # Scale image to fit the printable area while maintaining aspect ratio
            img_width, img_height = img.size
            scale_x = printable_width / img_width
            scale_y = printable_height / img_height
            scale = min(scale_x, scale_y)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # Center the image on the page
            x_offset = (printable_width - new_width) // 2
            y_offset = (printable_height - new_height) // 2

            # Use ImageWin to draw the image
            dib = ImageWin.Dib(img)
            dib.draw(
                hdc.GetHandleOutput(),
                (x_offset, y_offset, x_offset + new_width, y_offset + new_height)
            )

            hdc.EndPage()
            logger.info("Página %d impresa", page_num + 1)

        hdc.EndDoc()
        hdc.DeleteDC()

        logger.info("PDF enviado a %s (%d páginas)", target_printer, len(images))
        result: dict[str, object] = {
            "status": "sent",
            "message": f"PDF enviado a {target_printer} ({len(images)} páginas)",
            "printer": target_printer,
            "pages": len(images),
        }
        if paper_size is not None:
            result["paper_size"] = paper_size
        if has_custom_width and has_custom_height:
            result["paper_width_mm"] = paper_width_mm
            result["paper_height_mm"] = paper_height_mm
        return result

    except Exception as exc:
        raise SystemPrinterError(f"Error al imprimir: {exc}") from exc


def print_pdf_raw_to_printer(
    pdf_data: bytes,
    printer_name: str,
) -> dict:
    """Print PDF directly to printer using win32print (for PostScript/PCL printers).

    This sends the raw PDF to the printer. Only works if the printer
    natively supports PDF (most modern network printers do).
    """
    if win32print is None:
        out_dir = Path.home() / ".moviu_printer" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "raw_pdf_job.pdf"
        job_path.write_bytes(pdf_data)
        logger.info("Sistema no Windows: PDF guardado en %s", job_path)
        return {
            "status": "simulated",
            "message": f"PDF guardado en {job_path}",
            "printer": "none",
        }
    assert win32print is not None

    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("Moviu PDF Print", "", "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, pdf_data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
        logger.info("PDF RAW enviado a %s (%d bytes)", printer_name, len(pdf_data))
        return {
            "status": "sent",
            "message": f"PDF enviado directamente a {printer_name}",
            "printer": printer_name,
            "bytes": len(pdf_data),
        }
    finally:
        win32print.ClosePrinter(handle)


def print_raw_to_system_printer(
    payload: bytes,
    printer_name: str,
    document_name: str = "Moviu RAW Print",
) -> dict:
    """Send raw bytes directly to a local system printer spooler."""
    if not payload:
        raise SystemPrinterError("El payload RAW está vacío")

    if win32print is None:
        out_dir = Path.home() / ".moviu_printer" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "raw_print_job.bin"
        job_path.write_bytes(payload)
        logger.info("Sistema no Windows: RAW guardado en %s", job_path)
        return {
            "status": "simulated",
            "message": f"RAW guardado en {job_path}",
            "printer": "none",
            "bytes": len(payload),
        }

    assert win32print is not None

    handle = None
    try:
        handle = win32print.OpenPrinter(printer_name)
        win32print.StartDocPrinter(handle, 1, (document_name, "", "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            total_written = 0
            view = memoryview(payload)
            while total_written < len(payload):
                written = int(win32print.WritePrinter(handle, bytes(view[total_written: total_written + 65536])))
                if written <= 0:
                    raise SystemPrinterError(
                        f"WritePrinter devolvió {written} en offset {total_written}/{len(payload)}"
                    )
                total_written += written
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)

        logger.info("RAW enviado a %s (%d bytes)", printer_name, len(payload))
        return {
            "status": "sent",
            "message": f"RAW enviado directamente a {printer_name}",
            "printer": printer_name,
            "bytes": len(payload),
        }
    except SystemPrinterError:
        raise
    except Exception as exc:
        logger.exception("Error enviando RAW a la impresora %s", printer_name)
        raise SystemPrinterError(f"Error enviando RAW a '{printer_name}': {exc}") from exc
    finally:
        if handle is not None:
            win32print.ClosePrinter(handle)
