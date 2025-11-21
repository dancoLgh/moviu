"""Pequeño bridge TCP → USB para impresoras locales.

Escucha en un puerto TCP y envía cualquier payload recibido al dispositivo
USB configurado (por ejemplo `/dev/usb/lp0`). Pensado para casos donde un
servicio remoto solo puede hablar TCP pero la impresora está conectada por
USB a esta máquina.
"""

from __future__ import annotations

import logging
import socketserver
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

LOGGER = logging.getLogger(__name__)


class _BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler: Callable[..., socketserver.BaseRequestHandler], device_path: Path):
        self.device_path = device_path
        super().__init__(server_address, handler)


class _BridgeHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:  # noqa: D401 - socketserver contract
        """Recibe datos TCP y los envía al dispositivo USB configurado."""

        device_path = getattr(self.server, "device_path", None)
        if not device_path:
            LOGGER.error("Ruta de dispositivo USB no configurada; se cierra la conexión")
            return

        try:
            with open(device_path, "ab", buffering=0) as device:
                while True:
                    data = self.request.recv(4096)
                    if not data:
                        break
                    device.write(data)
            LOGGER.info("Trabajo TCP→USB enviado a %s", device_path)
        except FileNotFoundError:
            LOGGER.error("Dispositivo USB no encontrado en %s", device_path)
        except PermissionError:
            LOGGER.error("Sin permisos para escribir en %s", device_path)
        except OSError as exc:  # noqa: BLE001 - queremos loguear cualquier error de E/S
            LOGGER.error("Error al escribir en el dispositivo USB %s: %s", device_path, exc)


@dataclass
class BridgeConfig:
    host: str
    port: int
    device_path: Path


class TcpUsbBridge:
    """Controla el ciclo de vida del bridge TCP→USB."""

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.server: _BridgeServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.server:
            return

        handler = _BridgeHandler
        device_path = self.config.device_path
        server = _BridgeServer((self.config.host, self.config.port), handler, device_path)
        server.daemon_threads = True
        self.server = server
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        LOGGER.info(
            "Bridge TCP→USB escuchando en tcp://%s:%s → %s",
            self.config.host,
            self.config.port,
            device_path,
        )

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.server = None
        self.thread = None
        LOGGER.info("Bridge TCP→USB detenido")

    def restart(self, *, enabled: bool) -> None:
        self.stop()
        if enabled:
            self.start()

    def update_config(self, host: str, port: int, device_path: str) -> None:
        self.config = BridgeConfig(host=host, port=port, device_path=Path(device_path))
        if self.server:
            self.restart(enabled=True)

    def is_running(self) -> bool:
        return bool(self.server)


def default_bridge(host: str) -> TcpUsbBridge:
    """Crea un bridge con valores por defecto para que la app lo use fácilmente."""

    return TcpUsbBridge(BridgeConfig(host=host, port=9200, device_path=Path("/dev/usb/lp0")))
