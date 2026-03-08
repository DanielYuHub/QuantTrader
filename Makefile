.PHONY: help setup test lint compile run docker-build docker-up docker-down health migrate

help:
	@echo "Available targets: setup test compile run docker-build docker-up docker-down health migrate"

setup:
	python3.12 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -e .[dev]

test:
	pytest -q

compile:
	python -m compileall src tests scripts

run:
	python -m quant_trader.main

docker-build:
	docker build -t quant-trader:latest .

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

health:
	python scripts/healthcheck.py

migrate:
	python scripts/migrate.py
