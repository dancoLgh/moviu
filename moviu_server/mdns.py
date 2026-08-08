"""mDNS/DNS-SD service discovery using Zeroconf (Bonjour/Avahi compatible)."""

from __future__ import annotations

import logging
import socket
from typing import Optional, Callable

from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_local_ips() -> list[str]:
    """Return the IPv4 addresses that clients may use to reach this machine."""

    addresses = [get_local_ip()]
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address != "0.0.0.0" and address not in addresses:
                addresses.append(address)
    except OSError:
        pass
    return addresses


class MoviuServiceAnnouncer:
    """Announce the Moviu Print Server via mDNS/DNS-SD."""

    SERVICE_TYPE = "_moviu-print._tcp.local."
    SERVICE_NAME = "Moviu Print Server._moviu-print._tcp.local."

    def __init__(
        self,
        port: int,
        instance_name: str = "Moviu Print Server",
        properties: Optional[dict] = None,
    ) -> None:
        self.port = port
        self.instance_name = instance_name
        self.properties = properties or {}
        self.zeroconf: Optional[Zeroconf] = None
        self.service_info: Optional[ServiceInfo] = None

    def start(self) -> None:
        """Start announcing the service on the network."""
        if self.zeroconf:
            return

        try:
            local_ip = get_local_ip()
            hostname = socket.gethostname()

            # Build properties dict (must be bytes)
            props = {
                "version": "1.0",
                "hostname": hostname,
                "protocol": "https",
                **{k: str(v) for k, v in self.properties.items()}
            }

            self.service_info = ServiceInfo(
                self.SERVICE_TYPE,
                f"{self.instance_name}.{self.SERVICE_TYPE}",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=props,
                server=f"{hostname}.local.",
            )

            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)

            logger.info(
                "mDNS: Servicio anunciado como '%s' en %s:%d",
                self.instance_name,
                local_ip,
                self.port,
            )
        except Exception as exc:
            logger.error("mDNS: Error al iniciar el anuncio del servicio: %s", exc)
            self.zeroconf = None

    def stop(self) -> None:
        """Stop announcing the service."""
        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                logger.info("mDNS: Servicio desregistrado")
            except Exception as exc:
                logger.error("mDNS: Error al detener el servicio: %s", exc)
            finally:
                self.zeroconf = None
                self.service_info = None


class MoviuServiceDiscovery(ServiceListener):
    """Discover Moviu Print Servers on the local network."""

    def __init__(self, on_found: Optional[Callable[[dict], None]] = None) -> None:
        self.on_found = on_found
        self.services: list[dict] = []
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        info = zc.get_service_info(type_, name)
        if info:
            service_data = self._parse_service_info(info)
            self.services.append(service_data)
            logger.info("mDNS: Encontrado servicio: %s", service_data)
            if self.on_found:
                self.on_found(service_data)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""
        self.services = [s for s in self.services if s.get("name") != name]
        logger.info("mDNS: Servicio removido: %s", name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""
        self.remove_service(zc, type_, name)
        self.add_service(zc, type_, name)

    def _parse_service_info(self, info: ServiceInfo) -> dict:
        """Parse ServiceInfo into a dictionary."""
        addresses = [
            socket.inet_ntoa(addr) for addr in info.addresses
        ] if info.addresses else []

        properties = {}
        if info.properties:
            for key, value in info.properties.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8", errors="ignore")
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="ignore")
                properties[key] = value

        return {
            "name": info.name,
            "type": info.type,
            "server": info.server,
            "port": info.port,
            "addresses": addresses,
            "properties": properties,
        }

    def start(self, timeout: float = 3.0) -> list[dict]:
        """Start discovery and wait for services.

        Args:
            timeout: Seconds to wait for discovery.

        Returns:
            List of discovered services.
        """
        import time

        self.services = []
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(
            self.zeroconf,
            MoviuServiceAnnouncer.SERVICE_TYPE,
            self,
        )

        time.sleep(timeout)
        self.stop()
        return self.services

    def stop(self) -> None:
        """Stop discovery."""
        if self.browser:
            self.browser.cancel()
            self.browser = None
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None


def discover_moviu_servers(timeout: float = 3.0) -> list[dict]:
    """Discover Moviu Print Servers on the local network.

    Args:
        timeout: Seconds to wait for discovery.

    Returns:
        List of discovered services with their addresses and properties.
    """
    discovery = MoviuServiceDiscovery()
    return discovery.start(timeout=timeout)
