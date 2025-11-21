import logging
import platform
import socket
import threading
from pathlib import Path
from typing import Callable, List


if platform.system() == "Windows":
    import win32print  # type: ignore
    import win32api  # type: ignore
else:
    win32print = None  # type: ignore
    win32api = None  # type: ignore

logger = logging.getLogger(__name__)


def list_printers() -> List[str]:
    """Return installed printer names (Windows only)."""
    if win32print is None:
        logger.warning("Listar impresoras solo está disponible en Windows.")
        return []

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    return [printer[2] for printer in printers]


def send_raw_to_printer(printer_name: str, payload: bytes) -> None:
    """Send raw bytes to a printer (Windows) or store them locally on other OS."""
    if not payload:
        logger.info("Se recibió una conexión vacía; no se envió nada a la impresora.")
        return

    if win32print is None:
        out_dir = Path.home() / ".tcp_usb_bridge" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "job.bin"
        job_path.write_bytes(payload)
        logger.info("Sistema no Windows: se guardó el trabajo simulado en %s", job_path)
        return

    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("TCP USB Bridge", None, "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, payload)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
        logger.info("Trabajo enviado a %s (%d bytes)", printer_name, len(payload))
    finally:
        win32print.ClosePrinter(handle)


class PrinterServer:
    def __init__(self, printer_name: str, host: str, port: int, status_callback: Callable[[str], None] | None = None):
        self.printer_name = printer_name
        self.host = host
        self.port = port
        self.status_callback = status_callback
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(5)
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("Servidor TCP escuchando en %s:%d", self.host, self.port)
        if self.status_callback:
            self.status_callback(f"Escuchando en {self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._server:
            try:
                self._server.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._server.close()
            self._server = None
        if self.status_callback:
            self.status_callback("Servidor detenido")
        logger.info("Servidor detenido")

    def _serve(self) -> None:
        assert self._server is not None
        while self._running:
            try:
                client, address = self._server.accept()
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client, address), daemon=True).start()

    def _handle_client(self, client: socket.socket, address: tuple[str, int]) -> None:
        with client:
            logger.info("Conexión entrante de %s:%d", address[0], address[1])
            buffer = bytearray()
            try:
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)
            except ConnectionResetError:
                logger.info(
                    "El cliente %s:%d interrumpió la conexión de forma abrupta (reset)",
                    address[0],
                    address[1],
                )
            except OSError:
                logger.exception("Error recibiendo datos de %s:%d", address[0], address[1])
            else:
                if buffer:
                    send_raw_to_printer(self.printer_name, bytes(buffer))
                else:
                    logger.info("La conexión de %s:%d no envió datos", address[0], address[1])

        if self.status_callback:
            self.status_callback(f"Último cliente: {address[0]}:{address[1]}")
