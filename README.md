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
- Arbeit → Rechnungen: Stammdaten ausfüllen (`/arbeit/stammdaten`), Entwurf anlegen, ausstellen (mit Bestätigung), PDF herunterladen.
- Nur Caddy veröffentlicht einen Port, gebunden an `127.0.0.1` (Standard 80, änderbar über `HUB_HTTP_PORT`).

Nur der Kern, ohne Docker:

```bash
uv run uvicorn hub.main:app --reload
```

**Daten:** Kunden, Rechnungen und Stammdaten liegen im Docker-Volume `invoice-data` (SQLite), nie im Repo. `docker compose down -v` löscht dieses Volume und damit alle Rechnungen; bitte regelmäßig sichern. Ausgestellte Rechnungen sind unveränderlich; Korrekturen nur per Stornorechnung.

Plugins und Agenten hinzufügen: `docs/plugins.md`. Architektur: `docs/adr/ADR-001-plugin-architecture.md`.

## Umgebungsvariablen

| Variable | Bedeutung | Standard |
|---|---|---|
| `LOG_LEVEL` | Log-Level (stdout) | `INFO` |
| `PLUGINS_DIR` | Ordner mit `*/plugin.yaml` | `plugins` |
| `AGENTS_DIR` | Ordner mit `*/agent.yaml` | `agents` |
| `INVOICE_DB_PATH` | SQLite-Datei von `action-invoice` (im Container gesetzt) | `/data/invoice.sqlite` |
| `HUB_HTTP_PORT` | Host-Port von Caddy (nur `127.0.0.1`) | `80` |

## Checks und Tests

```bash
uv run ruff format . && uv run ruff check . --fix
uv run mypy src
uv run pytest
(cd plugins/source-hello && uv run pytest)
(cd plugins/action-invoice && uv run pytest && uv run mypy)
(cd frontend && npm run check && npm test)
```

Alles zusammen: `make test`. Die PDF-Tests von `action-invoice` brauchen lokal Pango (`brew install pango`), sonst werden sie übersprungen. Pre-Commit: `uv run pre-commit install`.

## Einzelner Kern-Container

```bash
docker build -t hub .
docker run --rm -p 127.0.0.1:8000:8000 hub
```
