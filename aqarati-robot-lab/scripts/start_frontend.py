"""Start Vite on the loopback interface only."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    subprocess.run(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=PROJECT_ROOT / "frontend", check=True)

