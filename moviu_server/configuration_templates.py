"""Community-extensible presets for the desktop configuration wizard.

Add a ConfigurationTemplate to CONFIGURATION_TEMPLATES to offer another USB
printer integration. The wizard derives its choices and steps from this catalog.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, replace

from .config import AppConfig


@dataclass(frozen=True)
class AccessMode:
    id: str
    label: str
    description: str
    shared: bool = False
    requires_api_key: bool = False


LOCAL_ACCESS = AccessMode(
    id="local",
    label="Solo en este equipo",
    description="Imprime desde esta computadora, sin API key y sin compartir la impresora.",
)
SHARED_ACCESS = AccessMode(
    id="shared",
    label="Compartir en la red local",
    description=(
        "Otros equipos podrán imprimir con API key. "
        "Se habilitará el acceso en el firewall para tu red local."
    ),
    shared=True,
    requires_api_key=True,
)
SHARED_WITHOUT_KEY_ACCESS = AccessMode(
    id="shared_without_key",
    label="Compartir en la red local sin API key",
    description=(
        "Otros equipos podrán imprimir sin clave. "
        "Se recomienda solo en redes privadas, controladas y seguras."
    ),
    shared=True,
)


@dataclass(frozen=True)
class ConfigurationTemplate:
    id: str
    label: str
    description: str
    access_modes: tuple[AccessMode, ...] = (LOCAL_ACCESS,)
    default_interface_mode: str = "simple"


CONFIGURATION_TEMPLATES = (
    ConfigurationTemplate(
        id="odoo",
        label="Odoo",
        description=(
            "Activa el puente USB y elige si imprimirás solo desde este equipo "
            "o compartirás la impresora en tu red local."
        ),
        access_modes=(LOCAL_ACCESS, SHARED_ACCESS, SHARED_WITHOUT_KEY_ACCESS),
    ),
    ConfigurationTemplate(
        id="chepos",
        label="ChePos",
        description=(
            "Elige tu impresora y empieza a imprimir desde este equipo. "
            "Sin API key y sin compartir automáticamente."
        ),
    ),
)


def get_template(template_id: str) -> ConfigurationTemplate:
    for template in CONFIGURATION_TEMPLATES:
        if template.id == template_id:
            return template
    raise ValueError("Selecciona una plantilla de configuración disponible.")


def build_template_config(
    base: AppConfig,
    template_id: str,
    printer_name: str,
    access_mode_id: str = "local",
) -> AppConfig:
    """Build a complete preset without mutating or persisting the base config."""
    template = get_template(template_id)
    mode = next((mode for mode in template.access_modes if mode.id == access_mode_id), None)
    if mode is None:
        raise ValueError("El modo de acceso no está disponible para esta plantilla.")
    if not printer_name.strip():
        raise ValueError("Selecciona la impresora para el puente USB.")
    if template.default_interface_mode not in {"simple", "advanced"}:
        raise ValueError("El modo de interfaz de la plantilla no es válido.")
    if not 1 <= base.port <= 65534 or not 1 <= base.usb_bridge_port <= 65535:
        raise ValueError("Los puertos configurados no son válidos.")
    ports = (base.port, base.port + 1, base.usb_bridge_port, 29170)
    if len(set(ports)) != len(ports):
        raise ValueError("Los puertos del servidor y del puente USB deben ser diferentes.")

    return replace(
        base,
        host="0.0.0.0" if mode.shared else "127.0.0.1",
        allow_without_api_key=not mode.requires_api_key,
        api_key=base.api_key or secrets.token_hex(16),
        printer_host="127.0.0.1",
        printer_port=base.usb_bridge_port,
        simulate_printer=False,
        usb_bridge_enabled=True,
        usb_bridge_printer=printer_name,
        usb_bridge_autostart=True,
        server_autostart=True,
        setup_completed=True,
        configuration_template=template.id,
        default_interface_mode=template.default_interface_mode,
    )
