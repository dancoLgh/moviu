"""Application configuration utilities."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".moviu_printer"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    """Configuration for the local printing server."""

    host: str = "127.0.0.1"
    port: int = 9000
    api_key: str = secrets.token_hex(16)
    printer_host: str = "192.168.0.100"
    printer_port: int = 9100

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "AppConfig":
        data = data or {}
        return cls(
            host=data.get("host", cls.host),
            port=int(data.get("port", cls.port)),
            api_key=data.get("api_key", secrets.token_hex(16)),
            printer_host=data.get("printer_host", cls.printer_host),
            printer_port=int(data.get("printer_port", cls.printer_port)),
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
