from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_ndjson(records: Iterable[dict], path: Path) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, default=str) + "\n")


def read_ndjson(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_many_ndjson(paths: Sequence[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        rows.extend(read_ndjson(path))
    return rows


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    ensure_parent(path)
    df.to_parquet(path, index=False)


def save_json(payload: dict, path: Path) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)

