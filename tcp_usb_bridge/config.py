import json
from dataclasses import dataclass, asdict
from pathlib import Path


CONFIG_PATH = Path.home() / ".tcp_usb_bridge" / "config.json"


@dataclass
class AppConfig:
    printer_name: str = ""
    port: int = 9100
    autostart: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return cls(
                printer_name=data.get("printer_name", ""),
                port=int(data.get("port", 9100)),
                autostart=bool(data.get("autostart", False)),
            )
        return cls()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
