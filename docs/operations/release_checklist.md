# Week 7 Release Checklist

Use this checklist before cutting the final submission tag or rebuilding the submission archive.

## 1. Environment

- Activate the project virtual environment.
- Confirm local tools exist:
  - `.venv/bin/python`
  - `.venv/bin/pytest`
  - `.venv/bin/ruff`
  - `docker`
- Keep the repo-root `docker-compose.yaml` as the preferred operator entrypoint; it includes `docker/compose.yaml`.

## 2. Validation

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
docker compose config >/dev/null
```

If Docker is available and the local stack can be started safely, also run:

```bash
make up
make smoke
make loadtest
```

## 3. Documentation alignment

- Confirm `README.md` and `submission/README.md` use the repo-root Compose entrypoint consistently.
- Confirm no final doc still uses placeholder status wording for assets that already ship.
- Confirm `Selected-base` is described as a model designation unless a real git tag has already been cut.
- Confirm the final write-up discloses the current burst-load result honestly:
  - `100 / 100` requests succeeded
  - HTTP request latency `p95 = 209.90 ms`

## 4. Submission bundle

```bash
make bundle
```

Then verify:

- `submission/fundamental_ai_crypto_volatile.zip` exists.
- `submission/README.md` matches the actual contents of `submission/`.
- The rebuilt zip is based on the current repo state, not the archived `archive/w4_deliverable/` snapshot.

## 5. Release reference

- Cut the final release tag only after the validation pass is green.
- Update any release-facing docs that still point to a placeholder or pre-release reference.
