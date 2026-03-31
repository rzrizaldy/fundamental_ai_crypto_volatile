from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "window_end_ts",
    "product_id",
    "midprice",
    "return_1s",
    "spread_bps",
    "tick_count_5s",
    "tick_count_15s",
    "tick_count_60s",
    "realized_vol_15s",
    "realized_vol_60s",
    "price_range_15s",
    "price_range_60s",
    "ewma_abs_return",
    "sigma_future_60s",
    "label",
    "source",
]


@dataclass(slots=True)
class FeatureConfig:
    bar_freq_seconds: int = 1
    target_horizon_seconds: int = 60
    ewma_span: int = 15
    tau_quantile: float = 0.90


def records_to_frame(records: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(list(records))
    if df.empty:
        return df

    df["event_ts"] = pd.to_datetime(df["event_ts"], utc=True)
    for column in [
        "price",
        "best_bid",
        "best_ask",
        "best_bid_quantity",
        "best_ask_quantity",
        "volume_24h",
    ]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.sort_values(["product_id", "event_ts"]).reset_index(drop=True)


def build_features(raw_df: pd.DataFrame, config: FeatureConfig, source: str) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    features: list[pd.DataFrame] = []
    for product_id, group in raw_df.groupby("product_id", sort=True):
        product_features = _build_product_features(product_id, group.copy(), config)
        product_features["source"] = source
        features.append(product_features)

    result = pd.concat(features, ignore_index=True)
    return result[FEATURE_COLUMNS]


def _build_product_features(product_id: str, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    df = df.set_index("event_ts").sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    bar_rule = f"{config.bar_freq_seconds}s"
    bars = (
        df.resample(bar_rule)
        .agg(
            {
                "price": "last",
                "best_bid": "last",
                "best_ask": "last",
            }
        )
        .rename(columns={"price": "last_price"})
    )

    tick_counts = df["price"].resample(bar_rule).count().rename("tick_count")
    bars = bars.join(tick_counts)
    bars[["last_price", "best_bid", "best_ask"]] = bars[
        ["last_price", "best_bid", "best_ask"]
    ].ffill()
    bars["tick_count"] = bars["tick_count"].fillna(0)

    bars["midprice"] = bars[["best_bid", "best_ask"]].mean(axis=1)
    bars["midprice"] = bars["midprice"].fillna(bars["last_price"])
    bars["return_1s"] = np.log(bars["midprice"]).diff()
    bars["spread_bps"] = (
        ((bars["best_ask"] - bars["best_bid"]) / bars["midprice"]) * 10_000
    )

    for window in (5, 15, 60):
        bars[f"tick_count_{window}s"] = (
            bars["tick_count"].rolling(window, min_periods=1).sum()
        )

    for window in (15, 60):
        bars[f"realized_vol_{window}s"] = (
            bars["return_1s"].rolling(window, min_periods=5).std()
        )
        rolling_mid = bars["midprice"].rolling(window, min_periods=5)
        bars[f"price_range_{window}s"] = (
            rolling_mid.max() - rolling_mid.min()
        ) / bars["midprice"]

    bars["ewma_abs_return"] = bars["return_1s"].abs().ewm(
        span=config.ewma_span,
        adjust=False,
        min_periods=3,
    ).mean()

    future_vol = bars["return_1s"].shift(-1).rolling(
        config.target_horizon_seconds,
        min_periods=max(10, config.target_horizon_seconds // 3),
    ).std()
    bars["sigma_future_60s"] = future_vol

    tau = float(bars["sigma_future_60s"].quantile(config.tau_quantile))
    if np.isnan(tau) or tau <= 0:
        tau = float(bars["sigma_future_60s"].dropna().median() or 0.0)
    bars["label"] = (bars["sigma_future_60s"] >= tau).astype("Int64")

    bars = bars.reset_index().rename(columns={"event_ts": "window_end_ts"})
    bars["window_end_ts"] = bars["window_end_ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    bars["product_id"] = product_id
    bars["label"] = bars["label"].fillna(0).astype(int)
    return bars


def feature_summary(features_df: pd.DataFrame) -> dict[str, float]:
    if features_df.empty:
        return {"rows": 0, "label_rate": 0.0, "tau_proxy": 0.0}
    return {
        "rows": float(len(features_df)),
        "label_rate": float(features_df["label"].mean()),
        "tau_proxy": float(features_df["sigma_future_60s"].quantile(0.90)),
    }

