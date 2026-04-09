from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn

from pipeline.config import load_config


def main() -> None:
    config = load_config()
    service_cfg = config["service"]
    uvicorn.run(
        "service.replay_api:app",
        host=service_cfg["host"],
        port=int(service_cfg["port"]),
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
