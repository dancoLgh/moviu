"""Display-independent state used by the desktop interface."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock


NAV_ITEMS = (
    ("home", "Inicio"),
    ("printers", "Impresoras"),
    ("connection", "Conexión"),
    ("activity", "Actividad"),
    ("settings", "Configuración"),
)


@dataclass(frozen=True)
class ActivityEvent:
    level: str
    message: str
    created_at: float

    @property
    def time_label(self) -> str:
        return datetime.fromtimestamp(self.created_at).strftime("%H:%M:%S")


class ActivityFeed:
    """Keep a bounded, thread-safe collection of application log events."""

    def __init__(self, max_events: int = 100) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be greater than zero")
        self._events: deque[ActivityEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def add(self, level: str, message: str, created_at: float) -> None:
        event = ActivityEvent(level=level, message=message, created_at=created_at)
        with self._lock:
            self._events.append(event)

    def recent(self, limit: int = 4) -> tuple[ActivityEvent, ...]:
        if limit <= 0:
            return ()
        with self._lock:
            return tuple(list(self._events)[-limit:][::-1])
