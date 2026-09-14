# ─────────────────────────────────────────────────────────────────────────────
# Lumen Space – Makefile
#
# Version management helpers for Django port.
#
# Usage:
#   make bump-patch   0.1.0 → 0.1.1  (bug-fixes, no breaking changes)
#   make bump-minor   0.1.0 → 0.2.0  (new features, backward-compatible)
#   make bump-major   0.1.0 → 1.0.0  (breaking changes)
# ─────────────────────────────────────────────────────────────────────────────

SHELL := /usr/bin/env bash -o pipefail
.DEFAULT_GOAL := help

VERSION_FILE := VERSION

CURRENT_VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null | tr -d '[:space:]' || echo "0.1.0")
MAJOR           := $(word 1, $(subst ., ,$(CURRENT_VERSION)))
MINOR           := $(word 2, $(subst ., ,$(CURRENT_VERSION)))
PATCH           := $(word 3, $(subst ., ,$(CURRENT_VERSION)))

.PHONY: help bump-patch bump-minor bump-major version _ensure-clean _do-bump test lint format

help: ## Show this help
	@echo ""
	@echo "  Lumen Space (Django) – version management"
	@echo ""
	@echo "  Current version: $$(cat $(VERSION_FILE) 2>/dev/null || echo '0.1.0')"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

version: ## Print the current version
	@echo "$(CURRENT_VERSION)"

test: ## Run full pytest test suite
	uv run pytest

lint: ## Run ruff and black checks
	uv run ruff check .
	uv run black --check .

format: ## Format code with black and ruff
	uv run ruff check --fix .
	uv run black .

_ensure-clean:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo ""; \
		echo "  ✗  Working tree is not clean. Commit or stash changes first."; \
		echo ""; \
		git status --short; \
		echo ""; \
		exit 1; \
	fi

_do-bump:
	@echo ""; \
	echo "  Bumping $(CURRENT_VERSION) → $(NEW_VERSION)"; \
	echo "$(NEW_VERSION)" > $(VERSION_FILE); \
	git add $(VERSION_FILE); \
	git commit -m "chore(release): bump version to v$(NEW_VERSION)"; \
	git tag -a "v$(NEW_VERSION)" -m "Release v$(NEW_VERSION)"; \
	echo ""; \
	echo "  ✓  Tagged v$(NEW_VERSION)"; \
	echo ""; \
	git push && git push --tags; \
	echo ""; \
	echo "  ✓  Pushed – CI will now build and publish ghcr.io image for v$(NEW_VERSION)"; \
	echo ""

bump-patch: _ensure-clean ## Bump patch version (bug-fixes)
	$(MAKE) _do-bump NEW_VERSION=$(MAJOR).$(MINOR).$(shell echo $$(($(PATCH)+1)))

bump-minor: _ensure-clean ## Bump minor version (new features)
	$(MAKE) _do-bump NEW_VERSION=$(MAJOR).$(shell echo $$(($(MINOR)+1))).0

bump-major: _ensure-clean ## Bump major version (breaking changes)
	$(MAKE) _do-bump NEW_VERSION=$(shell echo $$(($(MAJOR)+1))).0.0
