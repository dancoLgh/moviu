"""Logging configuration shared by the API server and desktop shell."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO


def build_uvicorn_log_config(log_file: Path, stream: TextIO) -> dict:
    """Build a Uvicorn config that lets access records reach desktop handlers."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "logging.Formatter",
                "fmt": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": stream,
            },
            "file": {
                "formatter": "default",
                "class": "logging.FileHandler",
                "filename": str(log_file),
                "mode": "a",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": [], "level": "INFO", "propagate": True},
            "uvicorn.error": {
                "handlers": [],
                "level": "INFO",
                "propagate": True,
            },
            "uvicorn.access": {"handlers": [], "level": "INFO", "propagate": True},
        },
    }
