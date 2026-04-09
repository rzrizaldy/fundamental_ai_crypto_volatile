from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]

SERVICES = (
    (
        "week4_api",
        [sys.executable, str(REPO_ROOT / "scripts/run_w4_api.py")],
        "http://localhost:8010/health",
    ),
    (
        "dashboard",
        [sys.executable, str(REPO_ROOT / "scripts/dashboard_server.py")],
        "http://localhost:8766/status",
    ),
)


def endpoint_is_up(url: str, timeout: float = 1.5) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def wait_for_service(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if endpoint_is_up(url):
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    managed_processes: list[subprocess.Popen] = []

    print("Starting CVI local demo stack...")
    for name, command, url in SERVICES:
        if endpoint_is_up(url):
            print(f"  - {name}: already running")
            continue

        print(f"  - {name}: launching")
        process = subprocess.Popen(command, cwd=REPO_ROOT)
        managed_processes.append(process)
        if wait_for_service(url):
            print(f"    {name} ready at {url}")
        else:
            raise RuntimeError(f"{name} did not become ready at {url}")

    print("\nLive endpoints:")
    print("  - Dashboard: http://localhost:8766/")
    print("  - Week 4 API: http://localhost:8010/health")
    print("\nPress Ctrl+C to stop any processes started by this launcher.")

    try:
        while True:
            for process in managed_processes:
                return_code = process.poll()
                if return_code is not None:
                    raise RuntimeError(f"Managed process exited early with code {return_code}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping managed demo processes...")
    finally:
        for process in managed_processes:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in managed_processes:
            if process.poll() is None:
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
