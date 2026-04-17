from __future__ import annotations

import contextlib
import importlib
import os
import sys
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

SAMPLE_ROWS = [
    {
        "return_1s": 0.0001,
        "spread_bps": 1.2,
        "tick_count_5s": 3,
        "tick_count_15s": 9,
        "tick_count_60s": 30,
        "realized_vol_15s": 0.0008,
        "realized_vol_60s": 0.0012,
        "price_range_15s": 0.15,
        "price_range_60s": 0.42,
        "ewma_abs_return": 0.0005,
    },
    {
        "return_1s": -0.0003,
        "spread_bps": 1.5,
        "tick_count_5s": 5,
        "tick_count_15s": 12,
        "tick_count_60s": 44,
        "realized_vol_15s": 0.0010,
        "realized_vol_60s": 0.0018,
        "price_range_15s": 0.22,
        "price_range_60s": 0.55,
        "ewma_abs_return": 0.0007,
    },
]


def _clear_prom_registry() -> None:
    """Drop any crypto_api_* collectors left behind by previous imports."""
    for collector in list(REGISTRY._collector_to_names.keys()):  # type: ignore[attr-defined]
        names = REGISTRY._collector_to_names.get(collector, set())  # type: ignore[attr-defined]
        if any(name.startswith("crypto_api_") for name in names):
            with contextlib.suppress(KeyError):
                REGISTRY.unregister(collector)


def _reload_app_with_variant(variant: str | None) -> object:
    for module_name in ("service.replay_api", "service"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    if variant is None:
        os.environ.pop("MODEL_VARIANT", None)
    else:
        os.environ["MODEL_VARIANT"] = variant

    _clear_prom_registry()

    return importlib.import_module("service.replay_api")


@pytest.fixture()
def ml_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("MODEL_VARIANT", "ml")
    module = _reload_app_with_variant("ml")
    with TestClient(module.app) as client:
        yield client


@pytest.fixture()
def baseline_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("MODEL_VARIANT", "baseline")
    module = _reload_app_with_variant("baseline")
    with TestClient(module.app) as client:
        yield client


def test_predict_variant_ml(ml_client: TestClient) -> None:
    resp = ml_client.post("/predict", json={"rows": SAMPLE_ROWS})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["model_variant"] == "ml"
    assert len(payload["scores"]) == len(SAMPLE_ROWS)
    for score in payload["scores"]:
        assert 0.0 <= score <= 1.0

    version_resp = ml_client.get("/version")
    assert version_resp.status_code == 200
    assert version_resp.json()["model_variant"] == "ml"
    assert version_resp.json()["model"] == "logistic_regression"


def test_predict_variant_baseline(baseline_client: TestClient) -> None:
    resp = baseline_client.post("/predict", json={"rows": SAMPLE_ROWS})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["model_variant"] == "baseline"
    assert len(payload["scores"]) == len(SAMPLE_ROWS)
    for score in payload["scores"]:
        assert 0.0 <= score <= 1.0

    version_resp = baseline_client.get("/version")
    assert version_resp.status_code == 200
    version_payload = version_resp.json()
    assert version_payload["model_variant"] == "baseline"
    assert version_payload["model"] == "baseline_zscore"

    health_resp = baseline_client.get("/health")
    assert health_resp.json()["model_variant"] == "baseline"


def test_startup_fails_on_unknown_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_VARIANT", "garbage")
    module = _reload_app_with_variant("garbage")
    with pytest.raises(ValueError, match="Unsupported MODEL_VARIANT"), TestClient(module.app):
        pass
