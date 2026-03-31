from __future__ import annotations

from pipeline.featurizer_core import FeatureConfig, build_features, records_to_frame


def test_build_features_returns_expected_columns() -> None:
    records = [
        {
            "event_ts": "2026-03-31T10:00:00Z",
            "ingest_ts": "2026-03-31T10:00:00Z",
            "product_id": "BTC-USD",
            "channel": "ticker",
            "price": 100.0,
            "best_bid": 99.9,
            "best_ask": 100.1,
            "best_bid_quantity": 1.0,
            "best_ask_quantity": 1.2,
            "volume_24h": 10.0,
            "source_sequence": 1,
            "raw_message": {},
        },
        {
            "event_ts": "2026-03-31T10:00:01Z",
            "ingest_ts": "2026-03-31T10:00:01Z",
            "product_id": "BTC-USD",
            "channel": "ticker",
            "price": 100.5,
            "best_bid": 100.4,
            "best_ask": 100.6,
            "best_bid_quantity": 1.0,
            "best_ask_quantity": 1.2,
            "volume_24h": 10.0,
            "source_sequence": 2,
            "raw_message": {},
        },
        {
            "event_ts": "2026-03-31T10:00:02Z",
            "ingest_ts": "2026-03-31T10:00:02Z",
            "product_id": "BTC-USD",
            "channel": "ticker",
            "price": 100.1,
            "best_bid": 100.0,
            "best_ask": 100.2,
            "best_bid_quantity": 1.0,
            "best_ask_quantity": 1.2,
            "volume_24h": 10.0,
            "source_sequence": 3,
            "raw_message": {},
        },
    ]

    raw_df = records_to_frame(records)
    features_df = build_features(raw_df, FeatureConfig(), source="test")
    assert not features_df.empty
    assert {
        "window_end_ts",
        "product_id",
        "midprice",
        "return_1s",
        "spread_bps",
        "sigma_future_60s",
        "label",
        "source",
    }.issubset(features_df.columns)
