.PHONY: run test check lint start stop health gpu docs help

PYTHON   ?= python3
VENV     ?= .venv
BACKEND  ?= backend_app.main

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

run: ## Start backend (uvicorn)
	KLIMTECH_EMBEDDING_DEVICE=cuda:0 $(PYTHON) -m uvicorn $(BACKEND):app --host 0.0.0.0 --port 8000 --reload

start: ## Full start (Qdrant + backend via start script)
	$(PYTHON) start_klimtech_v3.py

stop: ## Stop all services
	$(PYTHON) stop_klimtech.py

test: ## Run pytest
	$(PYTHON) -m pytest tests/ -v

check: ## Run project check script
	bash scripts/check_project.sh

lint: ## Lint backend code
	$(PYTHON) -m ruff check backend_app/

health: ## Quick backend health check
	curl -sk https://192.168.31.70:8443/health

gpu: ## GPU / model status
	curl -s http://192.168.31.70:8000/model/status
	curl -s http://192.168.31.70:8000/gpu/status

diag: ## Full diagnostics (G3 health check)
	$(PYTHON) scripts/health_check.py

docs: ## Open API docs in browser
	@echo "https://192.168.31.70:8443/docs"
