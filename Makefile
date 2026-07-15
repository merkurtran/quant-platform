SHELL := /bin/sh
.DEFAULT_GOAL := start

API_PORT ?= 8000
FRONTEND_PORT ?= 3000
COMPOSE_ENV ?= .env.docker
RUN_DIR := .run
LOG_DIR := $(RUN_DIR)/logs
SERVICES := api market-worker strategy-worker trade-executor frontend

.PHONY: install build migrate infra-up wait-infra infra-down start stop restart status logs deploy

install:
	cd backend && uv sync --frozen
	cd frontend && pnpm install --frozen-lockfile

build:
	cd frontend && pnpm build

infra-up:
	docker compose --env-file $(COMPOSE_ENV) up -d

wait-infra: infra-up
	@attempt=0; \
	until docker compose --env-file $(COMPOSE_ENV) exec -T postgres sh -c 'pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' >/dev/null 2>&1; do \
		attempt=$$((attempt + 1)); \
		if [ $$attempt -ge 30 ]; then echo "PostgreSQL did not become ready in 60 seconds"; exit 1; fi; \
		sleep 2; \
	done

migrate: wait-infra
	cd backend && uv run alembic upgrade head

infra-down:
	docker compose --env-file $(COMPOSE_ENV) down

start: migrate
	@mkdir -p $(LOG_DIR)
	@test -f frontend/.next/BUILD_ID || $(MAKE) build
	@$(call start_service,api,cd backend && exec uv run uvicorn app.main:app --host 0.0.0.0 --port $(API_PORT))
	@$(call start_service,market-worker,cd backend && exec uv run python workers/market_worker/main.py)
	@$(call start_service,strategy-worker,cd backend && exec uv run python workers/strategy_worker/scheduler.py)
	@$(call start_service,trade-executor,cd backend && exec uv run python workers/trade_executor/adapters/main.py)
	@$(call start_service,frontend,cd frontend && exec pnpm exec next start --hostname 0.0.0.0 --port $(FRONTEND_PORT))
	@echo "Services started: frontend http://localhost:$(FRONTEND_PORT), API http://localhost:$(API_PORT)"

deploy: install build start

stop:
	@for service in $(SERVICES); do \
		pid_file="$(RUN_DIR)/$$service.pid"; \
		if [ -f "$$pid_file" ]; then \
			pid=$$(cat "$$pid_file"); \
			if kill -0 "$$pid" 2>/dev/null; then kill "$$pid"; fi; \
			rm -f "$$pid_file"; \
			echo "Stopped $$service"; \
		fi; \
	done

restart: stop start

status:
	@for service in $(SERVICES); do \
		pid_file="$(RUN_DIR)/$$service.pid"; \
		if [ -f "$$pid_file" ] && kill -0 "$$(cat "$$pid_file")" 2>/dev/null; then \
			echo "RUNNING  $$service (PID $$(cat "$$pid_file"))"; \
		else \
			echo "STOPPED  $$service"; \
		fi; \
	done

logs:
	@mkdir -p $(LOG_DIR)
	tail -n 100 -f $(LOG_DIR)/*.log

define start_service
pid_file="$(RUN_DIR)/$(1).pid"; \
if [ -f "$$pid_file" ] && kill -0 "$$(cat "$$pid_file")" 2>/dev/null; then \
	echo "Already running: $(1)"; \
else \
	nohup sh -c '$(2)' > "$(LOG_DIR)/$(1).log" 2>&1 & \
	echo $$! > "$$pid_file"; \
	sleep 1; \
	if kill -0 "$$(cat "$$pid_file")" 2>/dev/null; then \
		echo "Started $(1) (PID $$(cat "$$pid_file"))"; \
	else \
		echo "Failed to start $(1); see $(LOG_DIR)/$(1).log"; \
		rm -f "$$pid_file"; \
		exit 1; \
	fi; \
fi
endef
