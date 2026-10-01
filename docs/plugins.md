# Plugins und Agenten hinzufügen

## Neues Plugin (source/action)

1. Ordner `plugins/<id>/` anlegen (Vorlage: `plugins/source-hello/`): MCP-Server, `Dockerfile`, eigene `pyproject.toml` und `uv.lock`, Tests.
2. `plugins/<id>/plugin.yaml` schreiben. Die Ordner-`id` muss der `id` im Manifest entsprechen. Schema: `src/hub/manifests.py`.
3. Service in `docker-compose.yml` ergänzen; die MCP-URL im Manifest nutzt den Service-Namen (`http://<id>:8000/mcp`).
4. Schreibende Tools: `writes: true` und `requires_confirmation: true`.
5. Secrets nur als Namen in `secrets:`, Werte in `.env` (Platzhalter in `.env.example`).

## Neuer Agent

Ordner `agents/<id>/` mit `agent.yaml` und der dort genannten Prompt-Datei anlegen. Kein Code nötig. Der Kern lädt Manifeste beim Start; nach Änderungen den Container `core` neu starten.

Prüfen: `GET http://hub.localhost/api/registry`.
