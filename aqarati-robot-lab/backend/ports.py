"""Loopback-only backend port selection and runtime discovery."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from . import paths
from .config import Settings

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
FALLBACK_PORT = 8010
RUNTIME_FILE = paths.data_path("processed", "backend-runtime.json")


class PortUnavailableError(RuntimeError):
    pass


def is_port_available(port: int) -> bool:
    """Check whether a TCP port can be bound on loopback without touching other processes."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((LOOPBACK_HOST, port))
        except OSError:
            return False
    return True


def select_backend_port(requested: int | None = None) -> tuple[int, bool]:
    """Return the requested port, or 8010 when the default 8000 is occupied."""
    port = requested if requested is not None else Settings.load().backend_port
    if is_port_available(port):
        return port, False
    if port == DEFAULT_PORT and is_port_available(FALLBACK_PORT):
        return FALLBACK_PORT, True
    raise PortUnavailableError(
        "Port {0} is occupied on {1}; no process was stopped.".format(port, LOOPBACK_HOST)
    )


def publish_runtime_port(port: int, fallback_used: bool) -> Path:
    payload = {
        "host": LOOPBACK_HOST,
        "port": port,
        "fallback_used": fallback_used,
    }
    return paths.write_text(RUNTIME_FILE, json.dumps(payload, indent=2) + "\n")


def read_runtime_port() -> int | None:
    if not RUNTIME_FILE.exists():
        return None
    try:
        payload = json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        port = int(payload.get("port"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return port if 1 <= port <= 65535 else None
