.PHONY: help install dev clean test lint fmt typecheck check docker-build docker-push

help:
	@echo "SecretMagic Makefile commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Install dev dependencies"
	@echo "  make clean        - Clean generated files"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make fmt          - Format code with ruff"
	@echo "  make isort        - Sort imports with ruff"
	@echo "  make typecheck    - Run mypy type checker"
	@echo "  make check        - Run all checks (fmt + lint + typecheck + test)"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-push  - Push Docker image to registry"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install -e .

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

lint:
	ruff check .

fmt:
	ruff format .

isort:
	ruff check --select I --fix .

typecheck:
	mypy src/

check: fmt isort lint typecheck test
	@echo "✅ All checks passed!"

docker-build:
	docker build -t cr.selcloud.ru/autoorder-platform/secretmagic:latest .

docker-push:
	docker push cr.selcloud.ru/autoorder-platform/secretmagic:latest

run:
	python -m src.main
