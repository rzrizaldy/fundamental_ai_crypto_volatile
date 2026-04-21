PYTHON ?= .venv/bin/python
COMPOSE := docker compose -f docker/compose.yaml

.PHONY: help up obs ps down logs config smoke loadtest bundle

help:
	@printf "Targets:\n"
	@printf "  make up        # build and start core services from docker/compose.yaml\n"
	@printf "  make obs       # start observability profile (Prometheus + Grafana)\n"
	@printf "  make ps        # show compose service status\n"
	@printf "  make logs      # tail compose logs\n"
	@printf "  make down      # stop compose services\n"
	@printf "  make config    # validate rendered compose config\n"
	@printf "  make smoke     # run replay smoke test with the selected Python\n"
	@printf "  make loadtest  # run the burst load test and refresh its report\n"
	@printf "  make bundle    # rebuild submission/fundamental_ai_crypto_volatile.zip\n"

up:
	$(COMPOSE) up -d --build

obs:
	$(COMPOSE) --profile observability up -d

ps:
	$(COMPOSE) ps

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs --tail=100

config:
	$(COMPOSE) config

smoke:
	$(PYTHON) scripts/replay_api_smoke.py --persist-slice

loadtest:
	$(PYTHON) scripts/replay_api_load_test.py --write-report reports/w5_load_test_latency.md

bundle:
	./scripts/build_submission_bundle.sh
