# Every command humans, agents and CI use. `make` lists them.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
PY ?= python3
export PYTHONPATH := src:tests
export SLIPWAY_HOME := $(CURDIR)

.PHONY: help install test lint format check smoke diagrams lock

help: ## List targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  \033[36mmake %-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Bootstrap this machine from this checkout (./install.sh)
	./install.sh

test: ## Unit tests (no network, temporary HOME)
	$(PY) -m unittest discover -s tests -t tests

lint: ## ruff, ruff format --check, shellcheck
	uvx ruff check src tests skills
	uvx ruff format --check src tests skills
	shellcheck install.sh

format: ## Apply ruff formatting
	uvx ruff format src tests skills

smoke: ## Dry-run install (base, every pack, each shipped profile) into a scratch HOME
	@set -eu; tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	  HOME=$$tmp $(PY) -m slipway install --all --dry-run >/dev/null; \
	  HOME=$$tmp $(PY) -m slipway install --profile edwin --dry-run >/dev/null; \
	  HOME=$$tmp $(PY) -m slipway install --profile claude-code --dry-run >/dev/null; \
	  HOME=$$tmp $(PY) -m slipway install --profile codex --dry-run >/dev/null; \
	  echo "smoke: dry-run ok for base, edwin, claude-code, codex"

check: lint test smoke ## The pre-push gate

diagrams: ## Regenerate docs/diagrams/*.svg and .drawio from their JSON specs
	@set -e; for spec in docs/diagrams/*.json; do $(PY) skills/arch-diagram/scripts/diagram.py "$$spec" -o "$${spec%.json}"; done

lock: ## Refresh slipway.lock.json from upstream and print the change report
	$(PY) -m slipway lock --refresh
