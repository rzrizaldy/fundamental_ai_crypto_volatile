# Docker Runbook Snippet

## What "runbook" means here

In Docker terms, a runbook is the operator cheat sheet for the Compose stack. It tells a reviewer or teammate exactly how to bring the containers up, check health, inspect logs, restart a failed service, and shut everything down safely.

## Markdown snippet

~~~md
## Docker service runbook

Use `docker/compose.yaml` as the single source of truth for the local stack.

### Bring the stack up

```bash
docker compose -f docker/compose.yaml up -d --build
docker compose -f docker/compose.yaml ps
```

Core services:
- `kafka` on `localhost:9094` for host-side clients
- `api` on `http://localhost:8000`
- `dashboard` on `http://localhost:8766`
- `mlflow` on `http://localhost:5001`

Optional observability profile:

```bash
docker compose -f docker/compose.yaml --profile observability up -d
```

Adds:
- `prometheus` on `http://localhost:9090`
- `grafana` on `http://localhost:3000`

### Basic operator checks

```bash
docker compose -f docker/compose.yaml ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/version
curl -s http://localhost:8000/metrics | head -n 20
```

### Logs and restart

```bash
docker compose -f docker/compose.yaml logs api --tail 100
docker compose -f docker/compose.yaml logs kafka --tail 100
docker compose -f docker/compose.yaml restart api
docker compose -f docker/compose.yaml restart kafka
```

### Shut the stack down

```bash
docker compose -f docker/compose.yaml down
```
~~~

Use this as the short-form insert for reports, submission docs, or a future expanded Docker operations section in the main runbook.
