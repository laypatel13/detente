# This machine's IP address on your team's private network, read from .env. When it's set, the
# tower answers there as well as on this machine, so teammates' laptops can reach it.
TOWER_ADDR := $(shell grep -s '^TOWER_ADDR=' .env | tail -n 1 | cut -d= -f2)
export TOWER_ADDR

SWITCH = docker compose -p detente-switch --env-file switch/.env -f switch/compose.yml $(if $(TOWER_ADDR),-f switch/share.yml) --profile collab --profile gateway
DETENTE = docker compose -p detente $(if $(TOWER_ADDR),-f docker-compose.yml -f docker-compose.share.yml)

.PHONY: install switch-up switch-down setup up down user api web dev test test-live test-crash record bench bench-real bench-planted

install:
	uv sync
	npm --prefix frontend install

switch-up:
	scripts/switch-env.sh
	$(SWITCH) up -d
	$(SWITCH) wait setup

switch-down:
	$(SWITCH) down

setup:
	uv run python -m backend.setup --registration-token "$$(grep ^AGENT_REGISTRATION_TOKEN= switch/.env | cut -d= -f2)"

up:
	$(DETENTE) up -d --build

down:
	$(DETENTE) down

user:
	docker compose -p detente exec api .venv/bin/python -m backend.accounts add $(NAME)

api:
	uv run uvicorn backend.main:app --port 8100 --env-file .env --reload --reload-dir backend

web:
	DETENTE_API_URL=http://localhost:8100 npm --prefix frontend run dev -- --port 3100

dev:
	$(MAKE) -j2 api web

test:
	uv run pytest

test-live:
	uv run python -m tests.live.run

test-crash:
	uv run python -m tests.live.run --restart

record:
	uv run python -m tests.live.record

bench:
	uv run python -m bench.run_bench

bench-real:
	uv run python -m bench.real_merges $(REPOS)

bench-planted:
	uv run python -m bench.planted $(REPOS)
