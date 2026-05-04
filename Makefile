.PHONY: test lint typecheck build all

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src/

build:
	uv build

all: lint typecheck test
