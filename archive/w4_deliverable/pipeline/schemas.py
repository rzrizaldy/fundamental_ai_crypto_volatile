from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class RawTick:
    event_ts: str
    ingest_ts: str
    product_id: str
    channel: str
    price: float | None
    best_bid: float | None
    best_ask: float | None
    best_bid_quantity: float | None
    best_ask_quantity: float | None
    volume_24h: float | None
    source_sequence: int | None
    raw_message: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

