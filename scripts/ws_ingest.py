from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import websockets

from pipeline.coinbase import build_subscribe_message, normalize_message
from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.io import write_ndjson
from pipeline.kafka_resilience import (
    attach_shutdown_handlers,
    recv_websocket_or_shutdown,
    safe_stop_client,
    send_with_producer_recovery,
    start_with_backoff,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream Coinbase ticker data to Kafka.")
    parser.add_argument("--minutes", type=int, default=0, help="How long to run the ingestor (0 = run forever).")
    parser.add_argument("--pair", action="append", dest="pairs", help="Product id to ingest. Repeatable.")
    parser.add_argument("--no-mirror", action="store_true", help="Disable NDJSON mirroring.")
    return parser.parse_args()


def raw_mirror_path(base_dir: Path, product_id: str, event_ts: str) -> Path:
    date_part = event_ts[:10]
    return base_dir / date_part / f"{product_id}.ndjson"


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(20),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def run_stream(
    websocket_url: str,
    product_ids: list[str],
    producer_cell: list[AIOKafkaProducer],
    bootstrap_servers: str,
    raw_topic: str,
    mirror_root: Path,
    mirror_enabled: bool,
    heartbeat_timeout_seconds: int,
    run_until: datetime | None,
    shutdown_event: asyncio.Event,
) -> None:
    timeout_deadline = datetime.now(UTC) + timedelta(seconds=heartbeat_timeout_seconds)
    producer_factory = lambda: AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async with websockets.connect(websocket_url, ping_interval=20, ping_timeout=20) as socket:
        for channel in ("ticker", "heartbeats"):
            await socket.send(json.dumps(build_subscribe_message(channel, product_ids)))

        while (run_until is None or datetime.now(UTC) < run_until) and not shutdown_event.is_set():
            payload = await recv_websocket_or_shutdown(
                socket,
                timeout_seconds=float(heartbeat_timeout_seconds),
                shutdown_event=shutdown_event,
            )
            if payload is None:
                print("Shutdown requested; closing WebSocket ingestor.")
                break
            message = json.loads(payload)
            message_type = message.get("type", "")

            if message_type in {"subscriptions", "error"}:
                print(json.dumps(message, indent=2))
                continue

            if message.get("channel") == "heartbeats":
                timeout_deadline = datetime.now(UTC) + timedelta(seconds=heartbeat_timeout_seconds)
                continue

            if datetime.now(UTC) > timeout_deadline:
                raise TimeoutError("Heartbeat timeout exceeded; reconnecting.")

            records = normalize_message(message)
            if not records:
                continue

            for record in records:
                await send_with_producer_recovery(
                    producer_cell,
                    producer_factory,
                    topic=raw_topic,
                    value=json.dumps(record).encode("utf-8"),
                )

            if mirror_enabled:
                bucketed: dict[Path, list[dict]] = defaultdict(list)
                for record in records:
                    bucketed[raw_mirror_path(mirror_root, record["product_id"], record["event_ts"])].append(record)
                for path, path_records in bucketed.items():
                    write_ndjson(path_records, path)


async def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config()
    ensure_directories(config)

    product_ids = args.pairs or list(config["stream"]["pairs"])
    bootstrap = config["stream"]["bootstrap_servers"]

    shutdown_event = asyncio.Event()
    attach_shutdown_handlers(shutdown_event)

    producer_factory = lambda: AIOKafkaProducer(bootstrap_servers=bootstrap)
    producer = await start_with_backoff(producer_factory, label="kafka producer")
    producer_cell = [producer]

    run_until = (
        datetime.now(UTC) + timedelta(minutes=args.minutes)
        if args.minutes > 0
        else None
    )
    print(f"Ingestor starting — pairs={product_ids} run_until={'forever' if run_until is None else run_until.isoformat()}")

    try:
        await run_stream(
            websocket_url=config["stream"]["websocket_url"],
            product_ids=product_ids,
            producer_cell=producer_cell,
            bootstrap_servers=bootstrap,
            raw_topic=config["stream"]["raw_topic"],
            mirror_root=ROOT_DIR / config["storage"]["raw_dir"],
            mirror_enabled=not args.no_mirror,
            heartbeat_timeout_seconds=config["stream"]["heartbeat_timeout_seconds"],
            run_until=run_until,
            shutdown_event=shutdown_event,
        )
    finally:
        await safe_stop_client(producer_cell[0])


if __name__ == "__main__":
    asyncio.run(main())