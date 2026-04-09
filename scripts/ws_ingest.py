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
    producer: AIOKafkaProducer,
    raw_topic: str,
    mirror_root: Path,
    mirror_enabled: bool,
    heartbeat_timeout_seconds: int,
    run_until: datetime | None,
) -> None:
    timeout_deadline = datetime.now(UTC) + timedelta(seconds=heartbeat_timeout_seconds)
    async with websockets.connect(websocket_url, ping_interval=20, ping_timeout=20) as socket:
        for channel in ("ticker", "heartbeats"):
            await socket.send(json.dumps(build_subscribe_message(channel, product_ids)))

        while run_until is None or datetime.now(UTC) < run_until:
            payload = await asyncio.wait_for(socket.recv(), timeout=heartbeat_timeout_seconds)
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
                await producer.send_and_wait(raw_topic, json.dumps(record).encode("utf-8"))

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

    # Retry Kafka connection on startup (Kafka may not be ready yet)
    for attempt in range(30):
        try:
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
            await producer.start()
            break
        except Exception as exc:
            if attempt == 29:
                raise
            print(f"Kafka not ready ({exc}), retrying in 5s… ({attempt + 1}/30)")
            await asyncio.sleep(5)

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
            producer=producer,
            raw_topic=config["stream"]["raw_topic"],
            mirror_root=ROOT_DIR / config["storage"]["raw_dir"],
            mirror_enabled=not args.no_mirror,
            heartbeat_timeout_seconds=config["stream"]["heartbeat_timeout_seconds"],
            run_until=run_until,
        )
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())