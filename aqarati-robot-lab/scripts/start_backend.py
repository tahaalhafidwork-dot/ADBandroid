"""Start the API on the loopback interface only."""

from __future__ import annotations

import sys
import os
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ports import LOOPBACK_HOST, publish_runtime_port, select_backend_port  # noqa: E402


if __name__ == "__main__":
    port, fallback_used = select_backend_port()
    os.environ["AQARATI_BACKEND_PORT"] = str(port)
    publish_runtime_port(port, fallback_used)
    if fallback_used:
        print("Port 8000 is occupied; no process was stopped.")
    print("Aqarati backend: http://{0}:{1}".format(LOOPBACK_HOST, port), flush=True)
    uvicorn.run("backend.main:app", host=LOOPBACK_HOST, port=port, reload=False)
