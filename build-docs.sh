#!/usr/bin/env bash

# This script is used to build the documentation on CloudFlare Pages, this is just used for build previews
# A different script with the same name exists on the `docs-site` branch (where pre-built docs live).

set -e
set -x

curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13
uv sync --python 3.13 --frozen --group docs

uv run --no-sync mkdocs build
