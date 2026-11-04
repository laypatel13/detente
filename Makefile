SWITCH = docker compose -p detente-switch --env-file switch/.env -f switch/compose.yml --profile collab --profile gateway

.PHONY: install switch-up switch-down setup up down user api web dev test test-live test-crash record bench bench-real

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
	docker compose -p detente up -d --build

down:
	docker compose -p detente down

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
