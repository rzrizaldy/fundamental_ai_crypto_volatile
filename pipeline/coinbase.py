from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .schemas import RawTick


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_subscribe_message(channel: str, product_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "subscribe",
        "product_ids": product_ids,
        "channel": channel,
    }


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_message(message: dict[str, Any]) -> list[dict[str, Any]]:
    channel = message.get("channel", "")
    records: list[dict[str, Any]] = []
    timestamp = message.get("timestamp") or utc_now_iso()
    ingest_ts = utc_now_iso()
    sequence_num = _to_int(message.get("sequence_num"))

    for event in message.get("events", []):
        for ticker in event.get("tickers", []):
            product_id = ticker.get("product_id")
            if not product_id:
                continue
            tick = RawTick(
                event_ts=ticker.get("event_time") or timestamp,
                ingest_ts=ingest_ts,
                product_id=product_id,
                channel=channel,
                price=_to_float(ticker.get("price")),
                best_bid=_to_float(ticker.get("best_bid")),
                best_ask=_to_float(ticker.get("best_ask")),
                best_bid_quantity=_to_float(ticker.get("best_bid_quantity")),
                best_ask_quantity=_to_float(ticker.get("best_ask_quantity")),
                volume_24h=_to_float(ticker.get("volume_24_h")),
                source_sequence=sequence_num,
                raw_message=message,
            )
            records.append(tick.to_dict())
    return records

