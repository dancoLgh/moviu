"""GitHub Release based updater for Moviu Print Server."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import secrets
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .config import CONFIG_DIR, VERSION

GITHUB_REPO = "dancoLgh/moviu"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
WEBSITE_DOWNLOAD_URL = "https://dancolgh.github.io/moviu/#descargas"
CHECKSUM_ASSET_NAME = "SHA256SUMS.txt"
MAX_UPDATE_SIZE = 250 * 1024 * 1024

ASSET_NAMES = {
    "win32": "MoviuPrintServer-Windows-x86_64.exe",
    "linux": "MoviuPrintServer-Linux-x86_64",
}
SUPPORTED_MACHINES = {"amd64", "x86_64"}
ALLOWED_DOWNLOAD_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}

logger = logging.getLogger(__name__)


class UpdateError(RuntimeError):
    """Raised when an update cannot be safely downloaded or installed."""


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove temporary update file: %s", path)


def _request_headers(token: Optional[str] = None, *, binary: bool = False) -> dict[str, str]:
    headers = {
        "User-Agent": "Moviu-Print-Server-Updater",
        "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_release_info(token: Optional[str] = None) -> Optional[dict]:
    """Fetch the latest release information from GitHub."""

    try:
        request = urllib.request.Request(GITHUB_API_URL, headers=_request_headers(token))
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Error checking for updates: %s", exc)
    return None


def _parse_version(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        raise ValueError(f"Versión no válida: {version}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def is_newer_release(info: Optional[dict], current_version: str = VERSION) -> bool:
    """Return whether release metadata describes a newer stable version."""

    if not info or info.get("draft") or info.get("prerelease"):
        return False
    try:
        return _parse_version(str(info.get("tag_name", ""))) > _parse_version(current_version)
    except ValueError:
        return False


def check_for_updates(token: Optional[str] = None) -> tuple[bool, Optional[str], Optional[str]]:
    """Check whether a newer release is available."""

    info = get_latest_release_info(token)
    if is_newer_release(info):
        return True, str(info["tag_name"]), WEBSITE_DOWNLOAD_URL
    return False, VERSION, None


def select_release_asset(
    info: dict,
    *,
    platform_name: Optional[str] = None,
    machine: Optional[str] = None,
) -> dict:
    """Select the binary asset matching the current supported platform."""

    platform_name = platform_name or sys.platform
    machine = (machine or platform.machine()).lower()
    if machine not in SUPPORTED_MACHINES or platform_name not in ASSET_NAMES:
        raise UpdateError("No hay una actualización automática para esta plataforma")

    expected_name = ASSET_NAMES[platform_name]
    for asset in info.get("assets", []):
        if asset.get("name") == expected_name:
            return asset
    raise UpdateError(f"El release no contiene {expected_name}")


def self_update_support(executable: Optional[Path] = None) -> tuple[bool, str]:
    """Describe whether this process can replace its packaged executable."""

    if not getattr(sys, "frozen", False):
        return False, "La aplicación se está ejecutando desde el código fuente"
    if sys.platform not in ASSET_NAMES or platform.machine().lower() not in SUPPORTED_MACHINES:
        return False, "La plataforma no tiene un binario de actualización compatible"

    target = executable or Path(sys.executable)
    if not target.is_file():
        return False, "La carpeta de la aplicación no permite reemplazar el ejecutable"
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=True):
            pass
    except OSError:
        return False, "La carpeta de la aplicación no permite reemplazar el ejecutable"
    return True, ""


def _is_allowed_download_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        hostname in ALLOWED_DOWNLOAD_HOSTS or hostname.endswith(".githubusercontent.com")
    )


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep release downloads on GitHub and never forward tokens across origins."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_allowed_download_url(newurl):
            raise UpdateError("GitHub redirigió la descarga a un destino no permitido")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlparse(req.full_url).netloc != urlparse(newurl).netloc:
            redirected.remove_header("Authorization")
        return redirected


def _download_asset(asset: dict, token: Optional[str] = None) -> bytes:
    url = asset.get("url") or asset.get("browser_download_url")
    if not url:
        raise UpdateError(f"El asset {asset.get('name', '')} no tiene URL de descarga")
    if not _is_allowed_download_url(url):
        raise UpdateError("La URL del asset no pertenece a GitHub")

    request = urllib.request.Request(url, headers=_request_headers(token, binary=True))
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=60) as response:
        data = response.read(MAX_UPDATE_SIZE + 1)
    if len(data) > MAX_UPDATE_SIZE:
        raise UpdateError("La actualización excede el tamaño máximo permitido")
    return data


def _expected_checksum(info: dict, asset_name: str, token: Optional[str]) -> str:
    checksum_asset = next(
        (asset for asset in info.get("assets", []) if asset.get("name") == CHECKSUM_ASSET_NAME),
        None,
    )
    if checksum_asset is None:
        raise UpdateError("El release no incluye el archivo de verificación SHA-256")

    checksum_text = _download_asset(checksum_asset, token).decode("utf-8")
    for line in checksum_text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[1].lstrip("*") == asset_name:
            checksum = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", checksum):
                return checksum
    raise UpdateError(f"No se encontró la firma SHA-256 de {asset_name}")


def download_update(
    info: dict,
    target_dir: Path,
    token: Optional[str] = None,
    *,
    platform_name: Optional[str] = None,
    machine: Optional[str] = None,
) -> Path:
    """Download and verify a release binary into the application directory."""

    asset = select_release_asset(info, platform_name=platform_name, machine=machine)
    asset_name = str(asset["name"])
    expected_checksum = _expected_checksum(info, asset_name, token)
    payload = _download_asset(asset, token)

    expected_size = int(asset.get("size") or 0)
    if expected_size and len(payload) != expected_size:
        raise UpdateError("La descarga no coincide con el tamaño publicado")
    if hashlib.sha256(payload).hexdigest() != expected_checksum:
        raise UpdateError("La verificación SHA-256 de la actualización ha fallado")

    suffix = ".exe" if (platform_name or sys.platform) == "win32" else ".bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".moviu-update-",
            suffix=suffix,
            dir=target_dir,
            delete=False,
        ) as stream:
            staged_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if suffix != ".exe":
            staged_path.chmod(0o755)
    except OSError as exc:
        if staged_path is not None:
            _unlink_quietly(staged_path)
        raise UpdateError(f"No se pudo guardar la actualización: {exc}") from exc
    assert staged_path is not None
    return staged_path


def _powershell_quote(path: Path) -> str:
    if any(character in str(path) for character in ("\x00", "\n", "\r")):
        raise UpdateError("La ruta de la aplicación no es compatible con el actualizador")
    return "'" + str(path).replace("'", "''") + "'"


def _windows_update_script(
    target: Path,
    staged: Path,
    ready_file: Path,
    armed_file: Path,
    ready_token: str,
    parent_pid: int,
) -> str:
    backup = target.with_name(f"{target.name}.old")
    return f"""$ErrorActionPreference = 'Stop'
$target = {_powershell_quote(target)}
$staged = {_powershell_quote(staged)}
$backup = {_powershell_quote(backup)}
$ready = {_powershell_quote(ready_file)}
$armed = {_powershell_quote(armed_file)}
$readyToken = '{ready_token}'
$backupCreated = $false
$env:PYINSTALLER_RESET_ENVIRONMENT = '1'
Set-Content -LiteralPath $armed -Value $readyToken -NoNewline -Encoding ascii
Wait-Process -Id {parent_pid} -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $armed -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
try {{
    Move-Item -LiteralPath $target -Destination $backup -Force
    $backupCreated = $true
    Move-Item -LiteralPath $staged -Destination $target -Force
    $env:MOVIU_UPDATE_READY_FILE = $ready
    $updated = Start-Process -FilePath $target -PassThru
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Path -LiteralPath $ready) -and (Get-Date) -lt $deadline -and -not $updated.HasExited) {{
        Start-Sleep -Milliseconds 250
        $updated.Refresh()
    }}
    if (-not (Test-Path -LiteralPath $ready) -or (Get-Content -LiteralPath $ready -Raw) -ne $readyToken) {{
        throw 'La nueva versión no confirmó el arranque'
    }}
    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $backup -Force
}} catch {{
    if ($updated -and -not $updated.HasExited) {{
        Stop-Process -Id $updated.Id -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $updated.Id -Timeout 5 -ErrorAction SilentlyContinue
    }}
    if ($backupCreated) {{
        Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $backup) {{ Move-Item -LiteralPath $backup -Destination $target -Force }}
    }}
    Remove-Item -LiteralPath $staged -Force -ErrorAction SilentlyContinue
    Remove-Item Env:MOVIU_UPDATE_READY_FILE -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $target) {{ Start-Process -FilePath $target }}
    Remove-Item -LiteralPath $armed -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
    exit 1
}}
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
"""


def _linux_update_script(
    target: Path,
    staged: Path,
    ready_file: Path,
    armed_file: Path,
    ready_token: str,
    parent_pid: int,
) -> str:
    backup = target.with_name(f"{target.name}.old")
    quoted_target = shlex.quote(str(target))
    quoted_staged = shlex.quote(str(staged))
    quoted_backup = shlex.quote(str(backup))
    quoted_ready = shlex.quote(str(ready_file))
    quoted_armed = shlex.quote(str(armed_file))
    return f"""#!/bin/sh
PYINSTALLER_RESET_ENVIRONMENT=1
export PYINSTALLER_RESET_ENVIRONMENT
printf %s "{ready_token}" > {quoted_armed}
while kill -0 {parent_pid} 2>/dev/null; do sleep 1; done
rm -f -- {quoted_armed}
rm -f -- {quoted_backup}
rm -f -- {quoted_ready}
if ! mv -- {quoted_target} {quoted_backup}; then
  rm -f -- {quoted_staged}
  {quoted_target} >/dev/null 2>&1 &
  rm -f -- "$0"
  exit 1
fi
if ! mv -- {quoted_staged} {quoted_target}; then
  rm -f -- {quoted_staged}
  mv -- {quoted_backup} {quoted_target}
  {quoted_target} >/dev/null 2>&1 &
  rm -f -- "$0"
  exit 1
fi
chmod +x {quoted_target}
MOVIU_UPDATE_READY_FILE={quoted_ready} {quoted_target} >/dev/null 2>&1 &
updated_pid=$!
attempt=0
while [ ! -f {quoted_ready} ] && kill -0 "$updated_pid" 2>/dev/null && [ "$attempt" -lt 120 ]; do
  sleep 0.25
  attempt=$((attempt + 1))
done
if [ -f {quoted_ready} ] && [ "$(cat {quoted_ready})" = "{ready_token}" ]; then
  rm -f -- {quoted_ready} {quoted_backup} "$0"
  exit 0
fi
kill "$updated_pid" 2>/dev/null || true
attempt=0
while kill -0 "$updated_pid" 2>/dev/null && [ "$attempt" -lt 20 ]; do
  sleep 0.25
  attempt=$((attempt + 1))
done
if kill -0 "$updated_pid" 2>/dev/null; then
  kill -9 "$updated_pid" 2>/dev/null || true
fi
wait "$updated_pid" 2>/dev/null || true
rm -f -- {quoted_target}
mv -- {quoted_backup} {quoted_target}
unset MOVIU_UPDATE_READY_FILE
{quoted_target} >/dev/null 2>&1 &
rm -f -- "$0"
exit 1
"""


def launch_self_update(
    staged_path: Path,
    *,
    executable: Optional[Path] = None,
    parent_pid: Optional[int] = None,
    platform_name: Optional[str] = None,
) -> subprocess.Popen:
    """Launch a detached helper that replaces the executable after this process exits."""

    target = (executable or Path(sys.executable)).resolve()
    staged_path = staged_path.resolve()
    platform_name = platform_name or sys.platform
    parent_pid = parent_pid or os.getpid()
    if staged_path.parent != target.parent:
        raise UpdateError("La actualización debe descargarse junto al ejecutable actual")

    ready_token = secrets.token_hex(16)
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.chmod(0o700)
    except OSError:
        raise UpdateError("No se pudo preparar el directorio privado del actualizador")
    ready_file = CONFIG_DIR / f"moviu-update-ready-{ready_token}"
    armed_file = CONFIG_DIR / f"moviu-update-armed-{ready_token}"
    _unlink_quietly(armed_file)
    if platform_name == "win32":
        script_text = _windows_update_script(
            target, staged_path, ready_file, armed_file, ready_token, parent_pid
        )
        suffix = ".ps1"
    elif platform_name == "linux":
        script_text = _linux_update_script(
            target, staged_path, ready_file, armed_file, ready_token, parent_pid
        )
        suffix = ".sh"
    else:
        raise UpdateError("La actualización automática no está disponible en esta plataforma")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="moviu-updater-",
            suffix=suffix,
            encoding="utf-8-sig" if platform_name == "win32" else "utf-8",
            delete=False,
        ) as stream:
            stream.write(script_text)
            script_path = Path(stream.name)
    except OSError as exc:
        raise UpdateError(f"No se pudo crear el instalador de actualización: {exc}") from exc

    try:
        if platform_name == "win32":
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                close_fds=True,
                creationflags=creation_flags,
            )
        else:
            script_path.chmod(0o700)
            process = subprocess.Popen(
                [str(script_path)],
                close_fds=True,
                start_new_session=True,
            )
    except Exception as exc:  # noqa: BLE001
        _unlink_quietly(script_path)
        raise UpdateError(f"No se pudo iniciar el instalador de actualización: {exc}") from exc

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            if armed_file.read_text(encoding="ascii") == ready_token:
                _unlink_quietly(armed_file)
                return process
        except OSError:
            pass
        if process.poll() is not None:
            break
        time.sleep(0.05)

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    _unlink_quietly(armed_file)
    _unlink_quietly(script_path)
    raise UpdateError("El instalador de actualización no pudo prepararse")


def acknowledge_update_startup() -> None:
    """Signal the replacement helper after the updated app initialized successfully."""

    ready_value = os.environ.pop("MOVIU_UPDATE_READY_FILE", "")
    if not ready_value:
        return
    ready_file = Path(ready_value).resolve()
    marker_match = re.fullmatch(r"moviu-update-ready-([0-9a-f]{32})", ready_file.name)
    if ready_file.parent != CONFIG_DIR.resolve() or marker_match is None:
        logger.warning("Ignored an invalid update readiness path: %s", ready_file)
        return
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(ready_file, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(marker_match.group(1))
    except OSError:
        logger.exception("Could not acknowledge successful update startup")


def open_release_page(url: str) -> None:
    """Open the supplied download page in the system browser."""

    webbrowser.open(url)
