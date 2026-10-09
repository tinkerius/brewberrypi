# BrewberryPi build commands (NFR-063). Overview: README.md, section "Development".

.DEFAULT_GOAL := help

CONTAINER ?= docker
IMAGE     ?= ghcr.io/tinkerius/brewberrypi
VERSION   := $(shell python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
PLATFORM  ?= linux/$(shell uname -m | sed -e 's/x86_64/amd64/' -e 's/aarch64/arm64/')

.PHONY: help setup frontend build image test lint format run dev clean

help:
	@echo "make setup     install Python and front-end dependencies"
	@echo "make build     build the front end and the Python wheel (dist/)"
	@echo "make image     build the container image $(IMAGE):$(VERSION) for $(PLATFORM)"
	@echo "make test      run the Python and front-end tests"
	@echo "make lint      ruff, mypy and the TypeScript type check"
	@echo "make format    auto-format and auto-fix lint findings"
	@echo "make run       run in simulation (--dummymode)"
	@echo "make dev       run in simulation plus the Vite dev server (live reload, port 5173)"
	@echo "make clean     remove build output and installed dependencies"

setup: frontend/node_modules
	uv sync

frontend/node_modules: frontend/package.json frontend/package-lock.json
	cd frontend && npm ci
	@touch $@

frontend: frontend/node_modules
	cd frontend && npm run build

build: frontend
	uv build --wheel

image:
	$(CONTAINER) build --platform $(PLATFORM) --build-arg VERSION=$(VERSION) \
		-f Containerfile -t $(IMAGE):$(VERSION) -t $(IMAGE):dev .

test: frontend/node_modules
	uv run pytest
	cd frontend && npm test

lint: frontend/node_modules
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	cd frontend && npm run typecheck

format:
	uv run ruff format .
	uv run ruff check --fix .

run:
	uv run brewberrypi --dummymode

# Back end and Vite dev server side by side; Ctrl+C stops both (same process group).
dev: frontend/node_modules
	uv run brewberrypi --dummymode & cd frontend && npm run dev; wait

clean:
	rm -rf dist build .venv .pytest_cache .mypy_cache .ruff_cache \
		src/brewberrypi/web/static frontend/node_modules
