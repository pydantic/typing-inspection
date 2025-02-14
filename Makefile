sources = src tests docs/hooks/

.PHONY: .uv  ## Check that uv is installed
.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

.PHONY: test
test: .uv
	uv run pytest --cov=typing_inspection

.PHONY: format
format: .uv
	uv run ruff format $(sources)

.PHONY: format-diff
format-diff: .uv
	uv run ruff format $(sources) --diff

.PHONY: lint
lint: .uv
	uv run ruff check $(sources)

.PHONY: lint-github
lint-github: .uv
	uv run ruff check $(sources) --output-format=github

.PHONY: typecheck
typecheck: .uv
	uv run pyright src/
