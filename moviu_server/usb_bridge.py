"""Helpers to manage the TCP → USB bridge inside the Moviu app."""

from __future__ import annotations

import logging
from typing import Callable, List

from tcp_usb_bridge.printer_bridge import PrinterServer, list_printers

logger = logging.getLogger(__name__)


def discover_printers() -> List[str]:
    """Return installed printers, logging a friendly message when none are found."""

    printers = list_printers()
    if not printers:
        logger.info(
            "No se detectaron impresoras USB. En Windows se listarán las instaladas en el sistema."
        )
    return printers


class UsbBridgeController:
    """Wrap the TCP → USB bridge server with a simple start/stop API."""

    def __init__(self, on_status: Callable[[str], None] | None = None) -> None:
        self.on_status = on_status
        self.server: PrinterServer | None = None

    def start(self, printer_name: str, port: int) -> None:
        if self.server:
            return

        logger.info("Levantando puente TCP → USB en el puerto %d", port)
        self.server = PrinterServer(printer_name, "0.0.0.0", port, self._notify_status)
        self.server.start()
        self._notify_status(f"Escuchando en 0.0.0.0:{port}")

    def stop(self) -> None:
        if not self.server:
            return

        logger.info("Deteniendo puente TCP → USB")
        self.server.stop()
        self.server = None
        self._notify_status("Puente detenido")

    def _notify_status(self, text: str) -> None:
        if self.on_status:
            self.on_status(text)
        logger.info(text)

