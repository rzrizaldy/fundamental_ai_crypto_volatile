# System Diagram

## Week 4 Thin Slice

```mermaid
flowchart LR
    A["Coinbase WebSocket<br/>public market data"] --> B["Kafka<br/>ticks.raw"]
    B --> C["Feature pipeline<br/>1-second bars + volatility features"]
    C --> D["Replay slice<br/>10-minute parquet window"]
    D --> E["FastAPI thin slice<br/>/health /predict /version /metrics"]
    F["logistic_model.joblib<br/>Selected-base artifact"] --> E
    G["MLflow<br/>run metadata + artifacts"] --> E
    E --> H["Prometheus scrape target<br/>/metrics"]
    H --> I["Grafana dashboard<br/>later weeks"]
    E --> J["Replay smoke test<br/>scripts/replay_api_smoke.py"]
```

## Interpretation
- **Live ingestion exists in the repo already**, but the Week 4 prototype intentionally runs the API in replay mode.
- **Kafka and MLflow still come up through Docker Compose** so the thin slice matches the later production path.
- **The FastAPI service loads a 10-minute replay window** from the current feature store and exposes prediction plus monitoring endpoints.
- **Prometheus/Grafana are represented in the interface contract now** through `/metrics`, even though the full dashboard stack can come in later weeks.

## What This Diagram Commits The Team To
- No model retraining inside the API thin slice
- No live websocket dependency for the Week 4 demo path
- One selected-base model artifact for the first service version
- Monitoring-compatible API surface from the first prototype
