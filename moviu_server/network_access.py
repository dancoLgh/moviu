"""Safely open Moviu's configured TCP ports to directly connected networks."""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import CONFIG_DIR


_FIREWALL_STATE_PATH = CONFIG_DIR / "firewall_rules.json"
_WINDOWS_RULE_NAMES = (
    "Moviu Print Server HTTPS",
    "Moviu Print Server Certificate HTTP",
    "Moviu Print Server USB Bridge",
)


class NetworkAccessError(RuntimeError):
    """Raised when local firewall access cannot be configured."""


@dataclass(frozen=True)
class NetworkAccessResult:
    firewall: str
    ports: tuple[int, ...]
    networks: tuple[str, ...] = ()
    rules_changed: bool = True


def _normalize_ports(*values: int | None) -> tuple[int, ...]:
    ports: list[int] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
            raise ValueError("Los puertos deben ser números enteros entre 1 y 65535")
        if value not in ports:
            ports.append(value)
    return tuple(ports)


def _configured_port_rules(
    api_port: int,
    bridge_port: int | None,
    certificate_port: int | None,
) -> tuple[tuple[str, int], ...]:
    candidates = (
        (_WINDOWS_RULE_NAMES[0], api_port),
        (_WINDOWS_RULE_NAMES[1], certificate_port),
        (_WINDOWS_RULE_NAMES[2], bridge_port),
    )
    rules: list[tuple[str, int]] = []
    used_ports: set[int] = set()
    for name, port in candidates:
        if port is None:
            continue
        normalized_port = _normalize_ports(port)[0]
        if normalized_port not in used_ports:
            rules.append((name, normalized_port))
            used_ports.add(normalized_port)
    return tuple(rules)


def is_local_network_bind(host: str) -> bool:
    """Return whether a bind host can accept connections from another device."""

    return host.strip().lower() not in {"127.0.0.1", "localhost", "::1"}


def _windows_elevation_command(rules: tuple[tuple[str, int], ...]) -> list[str]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"
    script_lines = ["$ErrorActionPreference = 'Stop'"]
    configured_names = {name for name, _port in rules}
    for rule_name, port in rules:
        script_lines.append(
            f"$rule = Get-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue; "
            f"if ($rule) {{ Set-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound "
            f"-Action Allow -Protocol TCP -LocalPort {port} -RemoteAddress LocalSubnet -Profile Any | Out-Null }} "
            f"else {{ New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -Action Allow "
            f"-Protocol TCP -LocalPort {port} -RemoteAddress LocalSubnet -Profile Any | Out-Null }}"
        )
    for rule_name in _WINDOWS_RULE_NAMES:
        if rule_name in configured_names:
            continue
        script_lines.append(
            f"Get-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue | Remove-NetFirewallRule"
        )
    encoded = base64.b64encode("; ".join(script_lines).encode("utf-16-le")).decode("ascii")
    elevation_script = (
        "$process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru "
        f"-ArgumentList '-NoProfile','-NonInteractive','-EncodedCommand','{encoded}'; "
        "exit $process.ExitCode"
    )
    return [powershell, "-NoProfile", "-NonInteractive", "-Command", elevation_script]


def _windows_removal_command() -> list[str]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"
    script = "$ErrorActionPreference = 'Stop'; " + "; ".join(
        f"Get-NetFirewallRule -DisplayName '{name}' -ErrorAction SilentlyContinue | Remove-NetFirewallRule"
        for name in _WINDOWS_RULE_NAMES
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    elevation_script = (
        "$process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru "
        f"-ArgumentList '-NoProfile','-NonInteractive','-EncodedCommand','{encoded}'; "
        "exit $process.ExitCode"
    )
    return [powershell, "-NoProfile", "-NonInteractive", "-Command", elevation_script]


def _local_ipv4_networks() -> tuple[str, ...]:
    ip_command = shutil.which("ip")
    if not ip_command:
        raise NetworkAccessError("No se encontró el comando 'ip' para detectar la red local")

    result = subprocess.run(
        [ip_command, "-o", "-4", "route", "show", "scope", "link"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NetworkAccessError(result.stderr.strip() or "No se pudo detectar la red local")

    networks: list[str] = []
    for line in result.stdout.splitlines():
        route = line.split(maxsplit=1)[0] if line.strip() else ""
        try:
            network = ipaddress.ip_network(route, strict=False)
        except ValueError:
            continue
        if network.version != 4 or network.is_loopback or network.is_link_local:
            continue
        value = str(network)
        if value not in networks:
            networks.append(value)
    if not networks:
        raise NetworkAccessError("No se encontró una subred IPv4 local conectada")
    return tuple(networks)


def _linux_elevation_prefix() -> list[str]:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    pkexec = shutil.which("pkexec")
    if not pkexec:
        raise NetworkAccessError(
            "Se requiere polkit (pkexec) para solicitar permisos de administrador desde la aplicación"
        )
    return [pkexec]


def _run_firewall_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "permiso cancelado"
        raise NetworkAccessError(f"No se pudo modificar el firewall: {detail}")


def _run_cleanup_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return
    detail = f"{result.stderr}\n{result.stdout}".strip()
    normalized = detail.lower()
    missing_rule = any(
        marker in normalized
        for marker in ("not_enabled", "not enabled", "non-existent", "not exist", "could not find")
    )
    if not missing_rule:
        raise NetworkAccessError(f"No se pudo reemplazar la regla anterior: {detail}")


def _firewalld_is_active(firewall_cmd: str) -> bool:
    result = subprocess.run(
        [firewall_cmd, "--state"], capture_output=True, text=True, check=False
    )
    return result.returncode == 0


def _ufw_is_active(ufw: str, prefix: list[str]) -> bool:
    result = subprocess.run(
        prefix + [ufw, "status"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "permiso cancelado"
        raise NetworkAccessError(f"No se pudo consultar el estado de UFW: {detail}")
    return "status: active" in result.stdout.lower()


def _firewalld_active_zones(firewall_cmd: str) -> tuple[str, ...]:
    result = subprocess.run(
        [firewall_cmd, "--get-active-zones"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise NetworkAccessError(result.stderr.strip() or "No se pudieron detectar las zonas activas")
    zones = tuple(line.strip() for line in result.stdout.splitlines() if line and not line[0].isspace())
    if zones:
        return zones

    result = subprocess.run(
        [firewall_cmd, "--get-default-zone"], capture_output=True, text=True, check=False
    )
    zone = result.stdout.strip()
    if result.returncode != 0 or not zone:
        raise NetworkAccessError(result.stderr.strip() or "No se pudo detectar la zona predeterminada")
    return (zone,)


def _load_firewall_state(state_path: Path) -> dict | None:
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _prepare_firewall_state(
    state_path: Path,
    firewall: str,
    ports: tuple[int, ...],
    networks: tuple[str, ...],
    zones: tuple[str, ...] = (),
) -> Path:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path = state_path.with_suffix(f"{state_path.suffix}.pending")
    pending_path.write_text(
        json.dumps(
            {
                "firewall": firewall,
                "ports": list(ports),
                "networks": list(networks),
                "zones": list(zones),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return pending_path


def _ufw_rule(ufw: str, network: str, port: int, delete: bool = False) -> list[str]:
    action = [ufw, "--force", "delete"] if delete else [ufw]
    return action + [
        "allow",
        "from",
        network,
        "to",
        "any",
        "port",
        str(port),
        "proto",
        "tcp",
    ]


def _firewalld_rule(network: str, port: int) -> str:
    return (
        f'rule family="ipv4" source address="{network}" '
        f'port port="{port}" protocol="tcp" accept'
    )


def _remove_previous_rules(
    state: dict | None,
    prefix: list[str],
    ufw: str | None,
    firewall_cmd: str | None,
) -> None:
    if not state:
        return
    try:
        ports = _normalize_ports(int(state["ports"][0]), None)
        for value in state["ports"][1:]:
            port = int(value)
            if port not in ports and 1 <= port <= 65535:
                ports += (port,)
        networks = tuple(str(ipaddress.ip_network(value, strict=False)) for value in state["networks"])
    except (KeyError, TypeError, ValueError, IndexError):
        return

    if state.get("firewall") == "ufw" and ufw:
        for network in networks:
            for port in ports:
                _run_cleanup_command(prefix + _ufw_rule(ufw, network, port, delete=True))
    elif state.get("firewall") == "firewalld" and firewall_cmd:
        zones = tuple(str(zone) for zone in state.get("zones", ()) if zone) or (None,)
        for zone in zones:
            zone_arg = [f"--zone={zone}"] if zone else []
            for network in networks:
                for port in ports:
                    rule = _firewalld_rule(network, port)
                    _run_cleanup_command(
                        prefix + [firewall_cmd, *zone_arg, f"--remove-rich-rule={rule}"]
                    )
                    _run_cleanup_command(
                        prefix
                        + [
                            firewall_cmd,
                            "--permanent",
                            *zone_arg,
                            f"--remove-rich-rule={rule}",
                        ]
                    )


def _restore_previous_rules(
    state: dict | None,
    prefix: list[str],
    ufw: str | None,
    firewall_cmd: str | None,
) -> None:
    if not state:
        return
    try:
        ports = _normalize_ports(int(state["ports"][0]), None)
        for value in state["ports"][1:]:
            port = int(value)
            if port not in ports and 1 <= port <= 65535:
                ports += (port,)
        networks = tuple(str(ipaddress.ip_network(value, strict=False)) for value in state["networks"])
    except (KeyError, TypeError, ValueError, IndexError):
        return

    if state.get("firewall") == "ufw" and ufw:
        for network in networks:
            for port in ports:
                _run_firewall_command(prefix + _ufw_rule(ufw, network, port))
    elif state.get("firewall") == "firewalld" and firewall_cmd:
        zones = tuple(str(zone) for zone in state.get("zones", ()) if zone) or (None,)
        for zone in zones:
            zone_arg = [f"--zone={zone}"] if zone else []
            for network in networks:
                for port in ports:
                    rule = _firewalld_rule(network, port)
                    _run_firewall_command(
                        prefix + [firewall_cmd, *zone_arg, f"--add-rich-rule={rule}"]
                    )
                    _run_firewall_command(
                        prefix
                        + [
                            firewall_cmd,
                            "--permanent",
                            *zone_arg,
                            f"--add-rich-rule={rule}",
                        ]
                    )


def _discard_pending_state(pending_path: Path) -> None:
    try:
        pending_path.unlink()
    except FileNotFoundError:
        pass


def open_local_network_ports(
    api_port: int,
    bridge_port: int | None = None,
    *,
    certificate_port: int | None = None,
    state_path: Path | None = None,
) -> NetworkAccessResult:
    """Open inbound TCP access for Moviu, restricted to local subnets."""

    rules = _configured_port_rules(api_port, bridge_port, certificate_port)
    ports = tuple(port for _name, port in rules)
    if sys.platform.startswith("win"):
        result = subprocess.run(_windows_elevation_command(rules), check=False)
        if result.returncode != 0:
            raise NetworkAccessError(
                "Windows no autorizó el cambio. Confirma el aviso de Control de cuentas de usuario."
            )
        return NetworkAccessResult(firewall="Firewall de Windows", ports=ports)

    if not sys.platform.startswith("linux"):
        raise NetworkAccessError("La apertura automática solo está disponible en Windows y Linux")

    networks = _local_ipv4_networks()
    prefix = _linux_elevation_prefix()
    ufw = shutil.which("ufw")
    firewall_cmd = shutil.which("firewall-cmd")
    state_path = state_path or _FIREWALL_STATE_PATH
    previous_state = _load_firewall_state(state_path)
    recovery_path = state_path.with_suffix(f"{state_path.suffix}.pending")
    recovery_state = _load_firewall_state(recovery_path)

    if firewall_cmd and _firewalld_is_active(firewall_cmd):
        zones = _firewalld_active_zones(firewall_cmd)
        _remove_previous_rules(recovery_state, prefix, ufw, firewall_cmd)
        _discard_pending_state(recovery_path)
        pending_path = _prepare_firewall_state(
            state_path, "firewalld", ports, networks, zones
        )
        added_commands: list[list[str]] = []
        try:
            _remove_previous_rules(previous_state, prefix, ufw, firewall_cmd)
            for zone in zones:
                zone_arg = [f"--zone={zone}"]
                for network in networks:
                    for port in ports:
                        rule = _firewalld_rule(network, port)
                        runtime_remove = prefix + [
                            firewall_cmd,
                            *zone_arg,
                            f"--remove-rich-rule={rule}",
                        ]
                        permanent_remove = prefix + [
                            firewall_cmd,
                            "--permanent",
                            *zone_arg,
                            f"--remove-rich-rule={rule}",
                        ]
                        _run_firewall_command(
                            prefix + [firewall_cmd, *zone_arg, f"--add-rich-rule={rule}"]
                        )
                        added_commands.append(runtime_remove)
                        _run_firewall_command(
                            prefix
                            + [
                                firewall_cmd,
                                "--permanent",
                                *zone_arg,
                                f"--add-rich-rule={rule}",
                            ]
                        )
                        added_commands.append(permanent_remove)
            pending_path.replace(state_path)
        except (NetworkAccessError, OSError) as exc:
            rollback_failed = False
            for command in reversed(added_commands):
                try:
                    _run_cleanup_command(command)
                except NetworkAccessError:
                    rollback_failed = True
            try:
                _restore_previous_rules(previous_state, prefix, ufw, firewall_cmd)
            except NetworkAccessError:
                pass
            if not rollback_failed:
                _discard_pending_state(pending_path)
            if isinstance(exc, NetworkAccessError):
                raise
            raise NetworkAccessError(f"No se pudo guardar el estado del firewall: {exc}") from exc
        return NetworkAccessResult(firewall="firewalld", ports=ports, networks=networks)

    if ufw and _ufw_is_active(ufw, prefix):
        _remove_previous_rules(recovery_state, prefix, ufw, firewall_cmd)
        _discard_pending_state(recovery_path)
        pending_path = _prepare_firewall_state(state_path, "ufw", ports, networks)
        added_commands: list[list[str]] = []
        try:
            _remove_previous_rules(previous_state, prefix, ufw, firewall_cmd)
            for network in networks:
                for port in ports:
                    _run_firewall_command(prefix + _ufw_rule(ufw, network, port))
                    added_commands.append(prefix + _ufw_rule(ufw, network, port, delete=True))
            pending_path.replace(state_path)
        except (NetworkAccessError, OSError) as exc:
            rollback_failed = False
            for command in reversed(added_commands):
                try:
                    _run_cleanup_command(command)
                except NetworkAccessError:
                    rollback_failed = True
            try:
                _restore_previous_rules(previous_state, prefix, ufw, firewall_cmd)
            except NetworkAccessError:
                pass
            if not rollback_failed:
                _discard_pending_state(pending_path)
            if isinstance(exc, NetworkAccessError):
                raise
            raise NetworkAccessError(f"No se pudo guardar el estado del firewall: {exc}") from exc
        return NetworkAccessResult(firewall="UFW", ports=ports, networks=networks)

    if ufw or firewall_cmd:
        if previous_state and previous_state.get("firewall") == "firewalld":
            raise NetworkAccessError(
                "firewalld está detenido y todavía existen reglas anteriores de Moviu. "
                "Inícialo para poder actualizarlas de forma segura."
            )
        return NetworkAccessResult(
            firewall="Sin firewall activo",
            ports=ports,
            networks=networks,
            rules_changed=False,
        )

    raise NetworkAccessError(
        "No se encontró un firewall compatible. Instala UFW o firewalld para usar esta función."
    )


def close_local_network_ports(*, state_path: Path | None = None) -> NetworkAccessResult:
    """Remove every firewall rule previously managed by Moviu."""

    if sys.platform.startswith("win"):
        result = subprocess.run(_windows_removal_command(), check=False)
        if result.returncode != 0:
            raise NetworkAccessError(
                "Windows no autorizó el cambio. Confirma el aviso de Control de cuentas de usuario."
            )
        return NetworkAccessResult(firewall="Firewall de Windows", ports=())

    if not sys.platform.startswith("linux"):
        raise NetworkAccessError("La apertura automática solo está disponible en Windows y Linux")

    state_path = state_path or _FIREWALL_STATE_PATH
    pending_path = state_path.with_suffix(f"{state_path.suffix}.pending")
    state = _load_firewall_state(state_path)
    pending_state = _load_firewall_state(pending_path)
    if not state and not pending_state:
        return NetworkAccessResult(
            firewall="Sin reglas administradas",
            ports=(),
            rules_changed=False,
        )

    prefix = _linux_elevation_prefix()
    ufw = shutil.which("ufw")
    firewall_cmd = shutil.which("firewall-cmd")
    managed_firewalls = {
        candidate.get("firewall")
        for candidate in (state, pending_state)
        if candidate
    }
    if "ufw" in managed_firewalls and not ufw:
        raise NetworkAccessError("No se encontró UFW para retirar las reglas anteriores de Moviu")
    if "firewalld" in managed_firewalls and (
        not firewall_cmd or not _firewalld_is_active(firewall_cmd)
    ):
        raise NetworkAccessError(
            "Inicia firewalld para retirar de forma segura las reglas anteriores de Moviu"
        )

    _remove_previous_rules(pending_state, prefix, ufw, firewall_cmd)
    _remove_previous_rules(state, prefix, ufw, firewall_cmd)
    _discard_pending_state(pending_path)
    try:
        state_path.unlink()
    except FileNotFoundError:
        pass
    return NetworkAccessResult(firewall="Firewall del sistema", ports=())
