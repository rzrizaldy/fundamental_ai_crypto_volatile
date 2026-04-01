from __future__ import annotations

from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from pipeline.config import ROOT_DIR, ensure_directories, load_config


def main() -> None:
    config = load_config()
    ensure_directories(config)
    dashboard_dir = ROOT_DIR / config["storage"]["dashboard_dir"]
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    features_path = ROOT_DIR / config["storage"]["processed_dir"] / "features.parquet"
    metrics_path = ROOT_DIR / config["storage"]["artifacts_dir"] / "metrics_summary.json"
    predictions_path = ROOT_DIR / config["storage"]["artifacts_dir"] / "predictions_latest.csv"

    payload: dict[str, object] = {"available": False}
    if features_path.exists():
        features_df = pd.read_parquet(features_path)
        payload["available"] = True
        payload["feature_rows"] = int(len(features_df))
        payload["label_rate"] = float(features_df["label"].mean()) if len(features_df) else 0.0
        latest = features_df.sort_values("window_end_ts").tail(120)
        payload["recent_volatility"] = latest[
            ["window_end_ts", "product_id", "realized_vol_60s", "sigma_future_60s"]
        ].to_dict(orient="records")
        payload["feature_distribution"] = (
            features_df[["spread_bps", "realized_vol_60s", "ewma_abs_return"]]
            .dropna()
            .head(400)
            .to_dict(orient="records")
        )
        # Full chart series for Chart.js — one entry per product
        chart_series: dict[str, list] = {}
        for product, grp in features_df.sort_values("window_end_ts").groupby("product_id"):
            chart_series[product] = grp[
                ["window_end_ts", "realized_vol_60s", "sigma_future_60s", "label", "midprice"]
            ].to_dict(orient="records")
        payload["chart_series"] = chart_series
        # Price summary
        price_summary: dict[str, dict] = {}
        for product, grp in features_df.groupby("product_id"):
            grp_sorted = grp.sort_values("window_end_ts")
            price_summary[product] = {
                "first": float(grp_sorted["midprice"].iloc[0]),
                "last": float(grp_sorted["midprice"].iloc[-1]),
                "delta_pct": float(
                    (grp_sorted["midprice"].iloc[-1] - grp_sorted["midprice"].iloc[0])
                    / grp_sorted["midprice"].iloc[0]
                    * 100
                ),
            }
        payload["price_summary"] = price_summary

    if metrics_path.exists():
        payload["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
    if predictions_path.exists():
        preds_df = pd.read_csv(predictions_path).tail(120)
        payload["predictions"] = preds_df.to_dict(orient="records")

    import math

    def _clean(obj):
        """Recursively replace float NaN/Inf with None for valid JSON."""
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    (dashboard_dir / "dashboard.json").write_text(
        json.dumps(_clean(payload), indent=2), encoding="utf-8"
    )
    print(f"Saved dashboard payload to {dashboard_dir / 'dashboard.json'}")


if __name__ == "__main__":
    main()
