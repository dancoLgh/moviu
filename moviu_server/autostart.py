"""Cross-platform helpers to register the app on OS startup."""

from __future__ import annotations

import logging
import os
import plistlib
import shlex
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def configure_autostart(enabled: bool) -> None:
    """Enable or disable app auto start according to ``enabled``."""

    if enabled:
        _enable_autostart()
    else:
        _disable_autostart()


def is_autostart_enabled() -> bool:
    """Return True if an autostart entry already exists."""

    path = _autostart_path()
    return path.exists() if path else False


def _enable_autostart() -> None:
    path = _autostart_path()
    if not path:
        raise RuntimeError("Ruta de autoinicio no disponible en este sistema")

    path.parent.mkdir(parents=True, exist_ok=True)
    command, args = _app_command()

    if sys.platform.startswith("win"):
        content = _windows_batch_content(command, args)
    elif sys.platform == "darwin":
        content = _mac_plist_content(command, args)
    else:
        content = _linux_desktop_content(command, args)

    if path.suffix == ".plist":
        with path.open("wb") as fh:
            plistlib.dump(content, fh)
    else:
        path.write_text(content, encoding="utf-8")

    LOGGER.info("Autoinicio habilitado en %s", path)


def _disable_autostart() -> None:
    path = _autostart_path()
    if path and path.exists():
        path.unlink()
        LOGGER.info("Autoinicio deshabilitado, se eliminó %s", path)


def _autostart_path() -> Path | None:
    if sys.platform.startswith("win"):
        appdata = os.getenv("APPDATA")
        if not appdata:
            return None
        return (
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "MoviuPrintServer.bat"
        )

    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / "com.moviu.printserver.plist"

    return Path.home() / ".config" / "autostart" / "moviu-print-server.desktop"


def _app_command() -> tuple[str, list[str]]:
    """Return executable and args to relaunch the app."""

    if getattr(sys, "frozen", False):
        return sys.executable, []

    root_dir = Path(__file__).resolve().parent.parent
    main_script = root_dir / "main.py"
    return sys.executable, [str(main_script)]


def _windows_batch_content(command: str, args: list[str]) -> str:
    quoted = " ".join(f'"{arg}"' for arg in [command, *args])
    return "\n".join(["@echo off", f"start \"\" {quoted}", "exit /b 0", ""])


def _linux_desktop_content(command: str, args: list[str]) -> str:
    exec_cmd = " ".join([shlex.quote(command), *(shlex.quote(arg) for arg in args)])
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=Moviu Print Server",
            "Exec=" + exec_cmd,
            "X-GNOME-Autostart-enabled=true",
            "Terminal=false",
            "",
        ]
    )


def _mac_plist_content(command: str, args: list[str]) -> dict:
    log_dir = Path.home() / ".moviu_printer"
    log_dir.mkdir(parents=True, exist_ok=True)
    return {
        "Label": "com.moviu.printserver",
        "ProgramArguments": [command, *args],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(log_dir / "autostart.log"),
        "StandardErrorPath": str(log_dir / "autostart.err"),
    }

