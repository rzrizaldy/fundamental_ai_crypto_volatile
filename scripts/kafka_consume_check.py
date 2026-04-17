from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from pipeline.config import load_config
from pipeline.kafka_resilience import safe_stop_client, start_with_backoff


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Kafka topic flow.")
    parser.add_argument("--topic", required=True, help="Topic to inspect.")
    parser.add_argument("--min", dest="min_messages", type=int, default=100, help="Minimum messages expected.")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Maximum wait time.")
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config()

    def make_consumer() -> AIOKafkaConsumer:
        return AIOKafkaConsumer(
            args.topic,
            bootstrap_servers=config["stream"]["bootstrap_servers"],
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=2_000,
        )

    consumer = await start_with_backoff(make_consumer, label="kafka consumer")
    try:
        deadline = datetime.now(UTC) + timedelta(seconds=args.timeout_seconds)
        message_count = 0
        products = Counter()
        event_times: list[str] = []
        while datetime.now(UTC) < deadline and message_count < args.min_messages:
            result = await consumer.getmany(timeout_ms=2_000, max_records=500)
            for records in result.values():
                for record in records:
                    payload = json.loads(record.value.decode("utf-8"))
                    message_count += 1
                    product_id = payload.get("product_id")
                    if product_id:
                        products[product_id] += 1
                    if payload.get("event_ts"):
                        event_times.append(payload["event_ts"])

        if message_count < args.min_messages:
            raise SystemExit(
                f"Only received {message_count} messages from {args.topic}; expected at least {args.min_messages}."
            )

        print(
            json.dumps(
                {
                    "topic": args.topic,
                    "messages": message_count,
                    "products": dict(products),
                    "start_event_ts": min(event_times) if event_times else None,
                    "end_event_ts": max(event_times) if event_times else None,
                },
                indent=2,
            )
        )
    finally:
        await safe_stop_client(consumer)


if __name__ == "__main__":
    asyncio.run(main())
