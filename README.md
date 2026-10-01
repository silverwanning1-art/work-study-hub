# Hub

Persönliches System zum Studieren und Arbeiten mit Plugin-Architektur (Quellen, Aktionen, Agenten, Kanäle) in einer Oberfläche. Projektplan: `Hub-System Projektplan.md`.

Arbeitsregeln für KI-Agents und Menschen: `AGENTS.md` und `docs/playbook/`.

## Setup

```bash
uv sync
cp .env.example .env
```

## Start

```bash
uv run uvicorn hub.main:app --reload
```

Health-Check: `GET http://127.0.0.1:8000/health` → `{"status": "ok"}`

## Umgebungsvariablen

| Variable | Bedeutung | Standard |
|---|---|---|
| `LOG_LEVEL` | Log-Level (stdout) | `INFO` |

## Checks und Tests

```bash
uv run ruff format . && uv run ruff check . --fix
uv run mypy src
uv run pytest
```

## Container

```bash
docker build -t hub .
docker run --rm -p 127.0.0.1:8000:8000 hub
```
