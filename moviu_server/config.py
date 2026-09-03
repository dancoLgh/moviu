"""Application configuration utilities."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".moviu_printer"
CONFIG_FILE = CONFIG_DIR / "config.json"
VERSION = "1.4.0"


@dataclass
class AppConfig:
    """Configuration for the local printing server."""

    host: str = "0.0.0.0"
    port: int = 9000
    api_key: str = secrets.token_hex(16)
    printer_host: str = "127.0.0.1"
    printer_port: int = 9100
    printer_width: int = 576
    printer_gamma: int = 500
    cut_margin_lines: int = 2
    simulate_printer: bool = False
    auto_start: bool = False
    usb_bridge_enabled: bool = False
    usb_bridge_port: int = 9100
    usb_bridge_printer: str = ""
    usb_bridge_autostart: bool = False
    ssl_cert_path: str = str(CONFIG_DIR / "cert.pem")
    ssl_key_path: str = str(CONFIG_DIR / "key.pem")
    github_token: str = ""

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "AppConfig":
        data = data or {}
        host = data.get("host", cls.host)
        cut_margin_lines = int(data.get("cut_margin_lines", cls.cut_margin_lines))
        if not 0 <= cut_margin_lines <= 20:
            cut_margin_lines = cls.cut_margin_lines
        # Migrate 127.0.0.1 to 0.0.0.0 to enable network access by default
        if host == "127.0.0.1":
            host = "0.0.0.0"

        return cls(
            host=host,
            port=int(data.get("port", cls.port)),
            api_key=data.get("api_key", secrets.token_hex(16)),
            printer_host=data.get("printer_host", cls.printer_host),
            printer_port=int(data.get("printer_port", cls.printer_port)),
            printer_width=int(data.get("printer_width", cls.printer_width)),
            printer_gamma=int(data.get("printer_gamma", cls.printer_gamma)),
            cut_margin_lines=cut_margin_lines,
            simulate_printer=bool(data.get("simulate_printer", cls.simulate_printer)),
            auto_start=bool(data.get("auto_start", cls.auto_start)),
            usb_bridge_enabled=bool(data.get("usb_bridge_enabled", cls.usb_bridge_enabled)),
            usb_bridge_port=int(data.get("usb_bridge_port", cls.usb_bridge_port)),
            usb_bridge_printer=data.get("usb_bridge_printer", cls.usb_bridge_printer),
            usb_bridge_autostart=bool(
                data.get("usb_bridge_autostart", cls.usb_bridge_autostart)
            ),
            ssl_cert_path=data.get("ssl_cert_path", str(cls.ssl_cert_path)),
            ssl_key_path=data.get("ssl_key_path", str(cls.ssl_key_path)),
            github_token=data.get("github_token", cls.github_token),
        )


def load_config() -> AppConfig:
    """Load configuration from disk."""

    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return AppConfig.from_dict(data)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = AppConfig()
    save_config(cfg)
    return cfg


def save_config(config: AppConfig) -> None:
    """Persist configuration to disk."""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w", encoding="utf-8") as fh:
        json.dump(asdict(config), fh, indent=2)
