from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv

from pipeline.config import ROOT_DIR, ensure_directories, load_config
from pipeline.featurizer_core import FeatureConfig, build_features, records_to_frame
from pipeline.io import save_parquet, write_ndjson


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume raw ticks and generate features.")
    parser.add_argument("--topic_in", default=None, help="Input topic.")
    parser.add_argument("--topic_out", default=None, help="Output topic.")
    parser.add_argument("--flush-every", type=int, default=500, help="Feature refresh cadence in messages.")
    parser.add_argument("--max-messages", type=int, default=0, help="Stop after this many messages. Zero means forever.")
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config()
    ensure_directories(config)

    feature_config = FeatureConfig(
        bar_freq_seconds=config["features"]["bar_freq_seconds"],
        target_horizon_seconds=config["features"]["target_horizon_seconds"],
        ewma_span=config["features"]["ewma_span"],
        tau_quantile=config["features"]["tau_quantile"],
    )

    topic_in = args.topic_in or config["stream"]["raw_topic"]
    topic_out = args.topic_out or config["stream"]["feature_topic"]
    processed_path = ROOT_DIR / config["storage"]["processed_dir"] / "features.parquet"

    consumer = AIOKafkaConsumer(
        topic_in,
        bootstrap_servers=config["stream"]["bootstrap_servers"],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        consumer_timeout_ms=2_000,
    )
    producer = AIOKafkaProducer(bootstrap_servers=config["stream"]["bootstrap_servers"])
    await consumer.start()
    await producer.start()

    raw_records: list[dict] = []
    last_emitted_ts: dict[str, str] = {}
    seen_messages = 0
    try:
        while True:
            result = await consumer.getmany(timeout_ms=2_000, max_records=args.flush_every)
            batch = []
            for records in result.values():
                for record in records:
                    batch.append(json.loads(record.value.decode("utf-8")))
            if not batch:
                if args.max_messages and seen_messages >= args.max_messages:
                    break
                continue

            raw_records.extend(batch)
            seen_messages += len(batch)

            raw_df = records_to_frame(raw_records)
            features_df = build_features(raw_df, feature_config, source="live")
            if features_df.empty:
                continue

            for product_id, group in features_df.groupby("product_id", sort=True):
                cutoff = last_emitted_ts.get(product_id)
                if cutoff:
                    group = group[group["window_end_ts"] > cutoff]
                if group.empty:
                    continue
                last_emitted_ts[product_id] = group["window_end_ts"].max()
                for _, row in group.iterrows():
                    await producer.send_and_wait(topic_out, row.to_json().encode("utf-8"))

            save_parquet(features_df, processed_path)
            if args.max_messages and seen_messages >= args.max_messages:
                break
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
