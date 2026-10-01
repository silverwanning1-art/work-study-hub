# Hub

Persönliches System zum Studieren und Arbeiten mit Plugin-Architektur (Quellen, Aktionen, Agenten, Kanäle) in einer Oberfläche. Projektplan: `Hub-System Projektplan.md`.

Arbeitsregeln für KI-Agents und Menschen: `AGENTS.md` und `docs/playbook/`.

## Setup

```bash
uv sync
cp .env.example .env
```

## Start

Gesamter Stack (Caddy, Kern, Frontend, `source-hello`):

```bash
make up      # docker compose up --build -d
make logs
make down
```

- UI: `http://hub.localhost` (Umschalter Studium/Arbeit, listet Plugins und Agenten)
- API: `http://api.localhost/health`, `http://hub.localhost/api/registry`
- Nur Caddy veröffentlicht einen Port, gebunden an `127.0.0.1` (Standard 80, änderbar über `HUB_HTTP_PORT`).

Nur der Kern, ohne Docker:

```bash
uv run uvicorn hub.main:app --reload
```

Plugins und Agenten hinzufügen: `docs/plugins.md`. Architektur: `docs/adr/ADR-001-plugin-architecture.md`.

## Umgebungsvariablen

| Variable | Bedeutung | Standard |
|---|---|---|
| `LOG_LEVEL` | Log-Level (stdout) | `INFO` |
| `PLUGINS_DIR` | Ordner mit `*/plugin.yaml` | `plugins` |
| `AGENTS_DIR` | Ordner mit `*/agent.yaml` | `agents` |
| `HUB_HTTP_PORT` | Host-Port von Caddy (nur `127.0.0.1`) | `80` |

## Checks und Tests

```bash
uv run ruff format . && uv run ruff check . --fix
uv run mypy src
uv run pytest
(cd plugins/source-hello && uv run pytest)
(cd frontend && npm run check)
```

Alles zusammen: `make test`. Pre-Commit: `uv run pre-commit install`.

## Einzelner Kern-Container

```bash
docker build -t hub .
docker run --rm -p 127.0.0.1:8000:8000 hub
```
