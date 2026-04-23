# Docker Runbook Snippet

## What "runbook" means here

In Docker terms, a runbook is the operator cheat sheet for the Compose stack. It tells a reviewer or teammate exactly how to bring the containers up, check health, inspect logs, restart a failed service, and shut everything down safely.

## Markdown snippet

~~~md
## Docker service runbook

Use the repo-root `compose.yaml` as the operator entrypoint. It includes `docker/compose.yaml`.

### Bring the stack up

```bash
docker compose up -d --build
docker compose ps
```

Core services:
- `kafka` on `localhost:9094` for host-side clients
- `ingestor` as the default Coinbase-to-Kafka stream worker
- `api` on `http://localhost:8000`
- `dashboard` on `http://localhost:8766`
- `mlflow` on `http://localhost:5001`

Optional observability profile:

```bash
docker compose --profile observability up -d
```

Adds:
- `prometheus` on `http://localhost:9090`
- `grafana` on `http://localhost:3000`

### Basic operator checks

```bash
docker compose ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/version
curl -s http://localhost:8000/metrics | head -n 20
```

### Logs and restart

```bash
docker compose logs ingestor --tail 100
docker compose logs api --tail 100
docker compose logs kafka --tail 100
docker compose restart api
docker compose restart kafka
```

### Shut the stack down

```bash
docker compose down
```
~~~

Use this as the short-form insert for reports, submission docs, or a future expanded Docker operations section in the main runbook.
