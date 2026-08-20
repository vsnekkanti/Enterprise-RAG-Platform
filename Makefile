.PHONY: up down test lint seed eval clean help

help:
	@echo "Enterprise RAG Platform - Make targets:"
	@echo "  make up        - Start all services (docker-compose)"
	@echo "  make down      - Stop all services"
	@echo "  make test      - Run pytest"
	@echo "  make lint      - Run ruff check and format"
	@echo "  make seed      - Seed database with arXiv PDFs"
	@echo "  make eval      - Run evaluation suite"
	@echo "  make clean     - Clean up containers, volumes, and cache"

up:
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker-compose ps

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	python3 -m pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src tests --select=E,F,W,I,N
	ruff format --check src tests

lint-fix:
	ruff check src tests --fix
	ruff format src tests

seed:
	python3 scripts/seed.py

eval:
	python3 scripts/eval.py

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache

smoke:
	python3 scripts/smoke_infra.py
