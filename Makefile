.PHONY: up down logs test

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src
	uv run pytest
	cd plugins/source-hello && uv run pytest
	cd plugins/source-rag && uv run pytest && uv run mypy
	cd plugins/action-invoice && uv run pytest && uv run mypy
	cd frontend && npm run check && npm test
