import hashlib
import logging
import platform
import socket
import threading
from pathlib import Path
from typing import Callable, List


if platform.system() == "Windows":
    import win32api  # type: ignore
    import win32print  # type: ignore
else:
    win32print = None  # type: ignore
    win32api = None  # type: ignore

logger = logging.getLogger(__name__)
_WRITE_LOCK = threading.Lock()


def list_printers() -> List[str]:
    """Return installed printer names (Windows only)."""
    if win32print is None:
        logger.warning("Listar impresoras solo esta disponible en Windows.")
        return []

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    return [printer[2] for printer in printers]


def printer_exists(printer_name: str) -> bool:
    """Return whether a Windows printer is currently installed/available."""
    if win32print is None:
        return True
    return printer_name in list_printers()


def _write_printer_all(handle: object, payload: bytes) -> int:
    """Write a payload to the spooler, handling partial writes."""
    assert win32print is not None

    total_written = 0
    view = memoryview(payload)
    payload_size = len(payload)

    while total_written < payload_size:
        chunk = bytes(view[total_written : total_written + 65536])
        written = int(win32print.WritePrinter(handle, chunk))
        if written <= 0:
            raise RuntimeError(
                f"WritePrinter returned {written} at offset {total_written}/{payload_size}"
            )
        total_written += written

    return total_written


def send_raw_to_printer(printer_name: str, payload: bytes) -> None:
    """Send raw bytes to a printer (Windows) or store them locally on other OS."""
    if not payload:
        logger.info("Se recibio una conexion vacia; no se envio nada a la impresora.")
        return

    if win32print is None:
        out_dir = Path.home() / ".tcp_usb_bridge" / "simulated_jobs"
        out_dir.mkdir(parents=True, exist_ok=True)
        job_path = out_dir / "job.bin"
        job_path.write_bytes(payload)
        logger.info("Sistema no Windows: se guardo el trabajo simulado en %s", job_path)
        return

    payload_size = len(payload)
    payload_hash = hashlib.sha256(payload).hexdigest()[:16]

    if not printer_exists(printer_name):
        raise RuntimeError(
            f"La impresora seleccionada no existe o no está disponible: {printer_name}"
        )

    # Serialize writes to avoid interleaving jobs in the same spooler.
    with _WRITE_LOCK:
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(handle, 1, ("TCP USB Bridge", None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                written = _write_printer_all(handle, payload)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)

    logger.info(
        "Job sent to %s (%d bytes, written=%d, sha256=%s)",
        printer_name,
        payload_size,
        written,
        payload_hash,
    )


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
            logger.info("Conexion entrante de %s:%d", address[0], address[1])
            buffer = bytearray()
            had_error = False
            try:
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)
            except ConnectionResetError:
                had_error = True
                logger.warning(
                    "El cliente %s:%d interrumpio la conexion de forma abrupta despues de %d bytes",
                    address[0],
                    address[1],
                    len(buffer),
                )
            except OSError:
                had_error = True
                logger.exception("Error recibiendo datos de %s:%d", address[0], address[1])

            if buffer and not had_error:
                try:
                    send_raw_to_printer(self.printer_name, bytes(buffer))
                except Exception as exc:
                    message = f"Error enviando a impresora USB '{self.printer_name}': {exc}"
                    logger.exception(message)
                    if self.status_callback:
                        self.status_callback(message)
            elif buffer and had_error:
                logger.warning(
                    "Se descarto un payload incompleto de %s:%d (%d bytes)",
                    address[0],
                    address[1],
                    len(buffer),
                )
            else:
                logger.info("La conexion de %s:%d no envio datos", address[0], address[1])

        if self.status_callback:
            self.status_callback(f"Ultimo cliente: {address[0]}:{address[1]}")
