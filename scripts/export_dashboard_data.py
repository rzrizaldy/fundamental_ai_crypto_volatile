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

    if metrics_path.exists():
        payload["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
    if predictions_path.exists():
        preds_df = pd.read_csv(predictions_path).tail(120)
        payload["predictions"] = preds_df.to_dict(orient="records")

    (dashboard_dir / "dashboard.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved dashboard payload to {dashboard_dir / 'dashboard.json'}")


if __name__ == "__main__":
    main()
