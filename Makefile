.DEFAULT_GOAL := all

.PHONY: .uv  ## Check that uv is installed
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: install
install: .uv  ## Install package and dependencies for local development
	uv sync --frozen --all-groups
	uv run pre-commit install --install-hooks

.PHONY: build-constraints
build-constraints: .uv  ## Generate the hashed constraints file for build dependencies, used when building in CI
	uv run --no-project python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['build-system']['requires']))" \
		| uv pip compile - --universal --python-version 3.10 --generate-hashes --upgrade \
			--custom-compile-command 'make build-constraints' -o .github/build-constraints.txt

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
