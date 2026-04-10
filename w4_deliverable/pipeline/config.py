from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import os

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged[key] = _deep_merge(base[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else ROOT_DIR / "config.yaml"
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    env_overrides: dict[str, Any] = {
        "stream": {
            "websocket_url": os.getenv("COINBASE_WS_URL", config["stream"]["websocket_url"]),
            "raw_topic": os.getenv("RAW_TOPIC", config["stream"]["raw_topic"]),
            "feature_topic": os.getenv("FEATURE_TOPIC", config["stream"]["feature_topic"]),
            "bootstrap_servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                config["stream"]["bootstrap_servers"],
            ),
        },
        "tracking": {
            "mlflow_tracking_uri": os.getenv(
                "MLFLOW_TRACKING_URI",
                config["tracking"]["mlflow_tracking_uri"],
            )
        },
    }
    return _deep_merge(config, env_overrides)


def ensure_directories(config: dict[str, Any]) -> None:
    paths = [
        ROOT_DIR / config["storage"]["raw_dir"],
        ROOT_DIR / config["storage"]["processed_dir"],
        ROOT_DIR / config["storage"]["artifacts_dir"],
        ROOT_DIR / config["storage"]["dashboard_dir"],
        ROOT_DIR / config["reports"]["img_dir"],
        ROOT_DIR / config["reports"]["evidently_dir"],
        ROOT_DIR / "handoff",
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

