# System Diagram

## Final Service Architecture

```mermaid
flowchart LR
    A["Coinbase WebSocket<br/>public market data"] --> B["Kafka<br/>ticks.raw"]
    B --> C["Feature pipeline<br/>1-second bars + volatility features"]
    C --> D["Replay slice<br/>10-minute parquet window"]
    D --> E["FastAPI replay service<br/>/health /predict /version /metrics"]
    F["logistic_model.joblib<br/>Selected-base artifact"] --> E
    G["MLflow<br/>run metadata + artifacts"] --> E
    E --> H["Prometheus scrape target<br/>/metrics"]
    H --> I["Grafana dashboard<br/>later weeks"]
    E --> J["Replay smoke test<br/>scripts/replay_api_smoke.py"]
```

## Interpretation
- **Live ingestion exists in the repo already**, while the packaged API path serves predictions from a replay slice for the stable demo flow.
- **Kafka and MLflow still come up through Docker Compose** so the shipped stack matches the repo's end-to-end operating path.
- **The FastAPI service loads a 10-minute replay window** from the current feature store and exposes prediction plus monitoring endpoints.
- **Prometheus/Grafana are part of the delivered observability surface** through `/metrics` and the provisioned dashboards.

## What This Diagram Commits The Repo To
- No model retraining inside the API service
- No live websocket dependency on the packaged replay-mode demo path
- One selected-base model artifact for the shipped service version
- Monitoring-compatible API surface with bundled observability assets
