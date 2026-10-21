"""Start Vite on the loopback interface only."""

from __future__ import annotations

import subprocess
import os
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Settings  # noqa: E402
from backend.ports import read_runtime_port  # noqa: E402


if __name__ == "__main__":
    environment = os.environ.copy()
    port = Settings.load().backend_port if os.environ.get("AQARATI_BACKEND_PORT") else (read_runtime_port() or 8000)
    environment["AQARATI_BACKEND_PORT"] = str(port)
    print("Vite proxy target: http://127.0.0.1:{0}".format(port), flush=True)
    npm_command = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_command:
        raise RuntimeError("npm was not found on PATH")
    subprocess.run(
        [npm_command, "run", "dev", "--", "--host", "127.0.0.1", "--config", "vite.config.ts"],
        cwd=PROJECT_ROOT / "frontend", check=True, env=environment,
    )
