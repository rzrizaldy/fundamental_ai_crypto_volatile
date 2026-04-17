from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import math
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from pipeline.config import ROOT_DIR, ensure_directories, load_config


def _clamp_probability(value: float, low: float = 0.05, high: float = 0.95) -> float:
    return max(low, min(high, float(value)))


def _mean_or_zero(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    value = float(series.mean())
    return 0.0 if pd.isna(value) else value


def _std_or_zero(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    value = float(series.std())
    return 0.0 if pd.isna(value) else value


def _directional_probability(returns: pd.Series) -> float:
    returns = returns.dropna()
    if returns.empty:
        return 0.5

    short = returns.tail(min(len(returns), 30))
    medium = returns.tail(min(len(returns), 120))

    short_signal = _mean_or_zero(short) / max(_std_or_zero(short), 1e-8)
    medium_signal = _mean_or_zero(medium) / max(_std_or_zero(medium), 1e-8)
    directional_score = 0.65 * short_signal + 0.35 * medium_signal
    up_probability = 0.5 + 0.22 * math.tanh(1.75 * directional_score)
    return _clamp_probability(up_probability, low=0.25, high=0.75)


def _projected_move(price: float, realized_vol: float, horizon_seconds: int, turbulence_probability: float) -> float:
    floor_fraction = 0.0015 if horizon_seconds <= 3600 else 0.004
    cap_fraction = 0.04 if horizon_seconds <= 3600 else 0.12
    turbulence_scale = 0.7 + 0.9 * turbulence_probability
    raw_move = price * max(realized_vol, 1e-6) * math.sqrt(horizon_seconds) * turbulence_scale
    return min(price * cap_fraction, max(price * floor_fraction, raw_move))


def _build_outlook(group: pd.DataFrame) -> dict[str, object]:
    group = group.sort_values("window_end_ts").reset_index(drop=True)
    latest = group.iloc[-1]

    vol_percentile = float(group["realized_vol_60s"].rank(pct=True).iloc[-1])
    latest_prob = latest.get("logistic_probability")
    if pd.isna(latest_prob):
        latest_prob = vol_percentile
    latest_prob = _clamp_probability(float(latest_prob))

    recent_window = group.tail(min(len(group), 60))["realized_vol_60s"]
    if len(group) >= 120:
        previous_window = group.iloc[-120:-60]["realized_vol_60s"]
    else:
        previous_window = group.head(max(len(group) // 2, 1))["realized_vol_60s"]

    prev_mean = max(_mean_or_zero(previous_window), 1e-9)
    trend_ratio = (_mean_or_zero(recent_window) - prev_mean) / prev_mean
    trend_score = _clamp_probability(0.5 + 0.35 * trend_ratio)
    session_pressure = _mean_or_zero(group.tail(min(len(group), 600))["label"])

    minute_up = _clamp_probability(0.85 * latest_prob + 0.15 * vol_percentile)
    hour_up = _clamp_probability(0.55 * latest_prob + 0.25 * vol_percentile + 0.20 * trend_score)
    day_up = _clamp_probability(
        0.30 * latest_prob + 0.35 * vol_percentile + 0.20 * session_pressure + 0.15 * trend_score
    )

    if hour_up >= 0.67:
        trend_label = "Higher turbulence likely"
    elif hour_up <= 0.33:
        trend_label = "Calmer conditions likely"
    else:
        trend_label = "Mixed, watch closely"

    return {
        "pair": latest["product_id"],
        "trend_label": trend_label,
        "volatility_percentile": vol_percentile,
        "trend_ratio": trend_ratio,
        "next_minute": {
            "higher_turbulence": minute_up,
            "calmer_conditions": 1 - minute_up,
        },
        "next_hour": {
            "higher_turbulence": hour_up,
            "calmer_conditions": 1 - hour_up,
        },
        "next_day": {
            "higher_turbulence": day_up,
            "calmer_conditions": 1 - day_up,
        },
        "student_summary": (
            f"{latest['product_id']} currently shows a {hour_up * 100:.0f}% chance of rougher-than-normal trading in the next hour "
            f"and a {day_up * 100:.0f}% chance that choppy conditions stay elevated into the next day. "
            "If you imagine a simple yes-or-no question like 'Will the market get rougher?', these percentages are the live odds. "
            "This is an educational turbulence outlook, not a price-direction forecast."
        ),
    }


def _build_price_scenario(group: pd.DataFrame) -> dict[str, object]:
    group = group.sort_values("window_end_ts").reset_index(drop=True)
    latest = group.iloc[-1]
    current_price = float(latest["midprice"])
    realized_vol = float(latest.get("realized_vol_60s") or 0.0)
    latest_prob = latest.get("logistic_probability")
    if pd.isna(latest_prob):
        latest_prob = 0.5
    latest_prob = _clamp_probability(float(latest_prob))

    returns = pd.to_numeric(group["return_1s"], errors="coerce")
    up_probability = _directional_probability(returns)
    down_probability = 1 - up_probability

    hour_move = _projected_move(current_price, realized_vol, 3600, latest_prob)
    day_move = _projected_move(current_price, realized_vol, 86400, latest_prob)

    if up_probability >= 0.57:
        bias_label = "UP BIAS"
    elif up_probability <= 0.43:
        bias_label = "DOWN BIAS"
    else:
        bias_label = "MIXED"

    return {
        "pair": latest["product_id"],
        "current_price": current_price,
        "bias_label": bias_label,
        "next_hour": {
            "up_probability": up_probability,
            "down_probability": down_probability,
            "up_move_usd": hour_move,
            "down_move_usd": hour_move,
            "up_target": current_price + hour_move,
            "down_target": current_price - hour_move,
        },
        "next_day": {
            "up_probability": up_probability,
            "down_probability": down_probability,
            "up_move_usd": day_move,
            "down_move_usd": day_move,
            "up_target": current_price + day_move,
            "down_target": current_price - day_move,
        },
        "summary": (
            f"{latest['product_id']} is trading near ${current_price:,.2f}. "
            f"The current directional bias is {bias_label.lower()}, based on recent return momentum. "
            f"A simple next-hour scenario is up ${hour_move:,.0f} to ${current_price + hour_move:,.0f} "
            f"or down ${hour_move:,.0f} to ${current_price - hour_move:,.0f}. "
            "This module is heuristic and complements the volatility outlook; it is not a directional model."
        ),
    }


def _clean(obj):
    if isinstance(obj, dict):
        return {key: _clean(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_clean(value) for value in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _iso_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _build_source_files() -> dict[str, dict[str, object]]:
    sources = {
        "model_eval_md": ROOT_DIR / "reports/model_eval.md",
        "evidently_report": ROOT_DIR / "reports/evidently/train_vs_test.html",
        "pr_curve": ROOT_DIR / "img/model_pr_curve.png",
        "predictions_csv": ROOT_DIR / "models/artifacts/predictions_latest.csv",
    }
    return {
        key: {
            "path": str(path.relative_to(ROOT_DIR)),
            "exists": path.exists(),
            "modified_at": _iso_mtime(path),
        }
        for key, path in sources.items()
    }


def _load_recent_mlflow_runs(db_path: Path, limit: int = 8) -> dict[str, object]:
    if not db_path.exists():
        return {
            "available": False,
            "ui_url": "http://localhost:5001/",
            "summary": {"total_runs": 0, "finished_runs": 0, "failed_runs": 0},
            "runs": [],
        }

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        summary_row = conn.execute(
            """
            SELECT
              COUNT(*) AS total_runs,
              SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) AS finished_runs,
              SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs
            FROM runs
            """
        ).fetchone()
        rows = conn.execute(
            """
            SELECT
              COALESCE(e.name, 'Default') AS experiment_name,
              r.run_uuid,
              r.status,
              datetime(r.start_time / 1000, 'unixepoch') AS started_at,
              datetime(r.end_time / 1000, 'unixepoch') AS ended_at,
              COALESCE(
                (
                  SELECT p.value
                  FROM params AS p
                  WHERE p.run_uuid = r.run_uuid AND p.key = 'model_type'
                  LIMIT 1
                ),
                '—'
              ) AS model_type
            FROM runs AS r
            LEFT JOIN experiments AS e
              ON e.experiment_id = r.experiment_id
            ORDER BY r.start_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    summary = {
        "total_runs": int(summary_row["total_runs"] or 0),
        "finished_runs": int(summary_row["finished_runs"] or 0),
        "failed_runs": int(summary_row["failed_runs"] or 0),
    }
    return {
        "available": summary["total_runs"] > 0,
        "ui_url": "http://localhost:5001/",
        "summary": summary,
        "runs": [dict(row) for row in rows],
    }


def _coerce_iso_timestamp(value: object) -> str | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return str(value)
    return ts.isoformat()


def main() -> None:
    config = load_config()
    ensure_directories(config)
    dashboard_dir = ROOT_DIR / config["storage"]["dashboard_dir"]
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    features_path = ROOT_DIR / config["storage"]["processed_dir"] / "features.parquet"
    metrics_path = ROOT_DIR / config["storage"]["artifacts_dir"] / "metrics_summary.json"
    predictions_path = ROOT_DIR / config["storage"]["artifacts_dir"] / "predictions_latest.csv"

    payload: dict[str, object] = {
        "available": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_files": _build_source_files(),
        "mlflow_runs": _load_recent_mlflow_runs(ROOT_DIR / "mlruns/mlflow.db"),
    }
    predictions_df = None
    if predictions_path.exists():
        predictions_df = pd.read_csv(predictions_path)
        if "probability" in predictions_df.columns and "logistic_probability" not in predictions_df.columns:
            predictions_df = predictions_df.rename(columns={"probability": "logistic_probability"})

    if features_path.exists():
        features_df = pd.read_parquet(features_path)
        features_df = features_df.sort_values(["window_end_ts", "product_id"]).reset_index(drop=True)

        if predictions_df is not None:
            merge_cols = ["window_end_ts", "product_id", "logistic_probability", "predicted_label"]
            features_df = features_df.merge(
                predictions_df[[column for column in merge_cols if column in predictions_df.columns]],
                on=["window_end_ts", "product_id"],
                how="left",
            )

        if "predicted_label" in features_df.columns:
            features_df["predicted_spike"] = features_df["predicted_label"].fillna(features_df["label"]).astype(int)
        else:
            features_df["predicted_spike"] = features_df["label"].astype(int)

        payload["available"] = True
        payload["feature_rows"] = int(len(features_df))
        payload["label_rate"] = float(features_df["label"].mean()) if len(features_df) else 0.0
        payload["data_window"] = {
            "start": _coerce_iso_timestamp(features_df["window_end_ts"].min()),
            "end": _coerce_iso_timestamp(features_df["window_end_ts"].max()),
        }
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

        chart_series: dict[str, list] = {}
        for product, grp in features_df.sort_values("window_end_ts").groupby("product_id"):
            chart_series[product] = grp[
                [
                    "window_end_ts",
                    "realized_vol_60s",
                    "sigma_future_60s",
                    "label",
                    "predicted_spike",
                    "logistic_probability",
                    "midprice",
                ]
            ].to_dict(orient="records")
        payload["chart_series"] = chart_series

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

        spike_rows = (
            features_df[features_df["predicted_spike"] == 1]
            .sort_values("window_end_ts", ascending=False)
            .groupby("product_id", group_keys=False)
            .head(6)
            .sort_values("window_end_ts", ascending=False)
            .head(12)
        )
        payload["recent_spikes"] = spike_rows[
            [
                "window_end_ts",
                "product_id",
                "midprice",
                "realized_vol_60s",
                "logistic_probability",
            ]
        ].to_dict(orient="records")

        payload["probability_outlook"] = {
            product: _build_outlook(grp)
            for product, grp in features_df.groupby("product_id", sort=True)
        }
        payload["price_scenarios"] = {
            product: _build_price_scenario(grp)
            for product, grp in features_df.groupby("product_id", sort=True)
        }

    if metrics_path.exists():
        payload["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))

    if predictions_df is not None:
        payload["predictions"] = predictions_df.tail(120).to_dict(orient="records")
        if "window_end_ts" in predictions_df.columns and not predictions_df.empty:
            payload["latest_prediction_ts"] = str(predictions_df["window_end_ts"].iloc[-1])

    (dashboard_dir / "dashboard.json").write_text(
        json.dumps(_clean(payload), indent=2),
        encoding="utf-8",
    )
    print(f"Saved dashboard payload to {dashboard_dir / 'dashboard.json'}")


if __name__ == "__main__":
    main()
