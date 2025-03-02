.DEFAULT_GOAL := all

.PHONY: .uv  ## Check that uv is installed
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install
install: .uv  ## Install package and dependencies for local development
	uv sync --frozen --all-groups
	uv run pre-commit install --install-hooks

.PHONY: test
test:
	uv run pytest --cov=typing_inspection

.PHONY: format
format:
	uv run ruff format
	uv run ruff check --fix --fix-only

.PHONY: format-diff
format-diff:
	uv run ruff format --diff

.PHONY: lint
lint:
	uv run ruff format --check
	uv run ruff check

.PHONY: lint-github
lint-github:
	uv run ruff check --output-format=github

.PHONY: typecheck
typecheck:
	uv run pyright

.PHONY: all
all: format lint typecheck test
