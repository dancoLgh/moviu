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
) -> dict:
    """Print a PDF to a system printer (laser, inkjet, etc.).

    Renders the PDF to images and prints each page using Windows GDI.

    Args:
        pdf_data: Raw PDF bytes.
        printer_name: Name of the printer. If None, uses default printer.
        dpi: Resolution for rendering (default 150 for good quality/speed balance).

    Returns:
        dict with status and details.
    """
    if platform.system() != "Windows":
        # For non-Windows, save to temp and log
        out_dir = Path.home() / ".moviu_printer" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "system_print_job.pdf"
        job_path.write_bytes(pdf_data)
        logger.info("Sistema no Windows: PDF guardado en %s", job_path)
        return {
            "status": "simulated",
            "message": f"PDF guardado en {job_path} (no Windows)",
            "printer": "none",
        }

    if win32print is None or win32ui is None:
        raise SystemPrinterError("win32print/win32ui no disponible")

    # Get printer name
    if printer_name:
        target_printer = printer_name
    else:
        target_printer = win32print.GetDefaultPrinter()

    if not target_printer:
        raise SystemPrinterError("No hay impresora predeterminada configurada")

    # Render PDF to images
    images = _render_pdf_to_images(pdf_data, dpi=dpi)

    try:
        # Create device context for printer
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(target_printer)

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
        return {
            "status": "sent",
            "message": f"PDF enviado a {target_printer} ({len(images)} páginas)",
            "printer": target_printer,
            "pages": len(images),
        }

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

    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("Moviu PDF Print", None, "RAW"))
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

