# ADR-001: Plugin-Architektur mit MCP als Plugin-Protokoll

Datum: 2026-10-01 · Status: angenommen

## Kontext

Das Hub-System soll viele Quellen und Agenten in einer Oberfläche bündeln. Neue Fähigkeiten sollen hinzukommen, ohne den Kern zu ändern (Projektplan, Abschnitt 3).

## Entscheidung

- Es gibt vier Plugin-Typen: `source`, `action`, `agent`, `channel`.
- **Source- und Action-Plugins sind MCP-Server** (offizielles `mcp`-SDK, Transport Streamable HTTP), je ein Container. Sie sind damit auch direkt aus Claude Desktop und Claude Code nutzbar.
- Jedes Plugin hat eine `plugin.yaml`, jeder Agent eine `agent.yaml` plus Prompt-Datei. Der Kern validiert sie beim Start mit Pydantic (`src/hub/manifests.py`); ungültige Manifeste werden übersprungen und geloggt.
- Schreibende Tools (`writes: true`) MÜSSEN `requires_confirmation: true` setzen. Der Kern ruft schreibende Tools erst auf, wenn der Bestätigungsflow existiert (spätere Phase).
- Der Kern ruft nur Tools auf, die im Manifest deklariert sind.
- **Caddy** ist der lokale Reverse Proxy (`hub.localhost`, `api.localhost`), nur auf `127.0.0.1` gebunden. Das Playbook-Referenzsetup (Traefik + oauth2-proxy) gilt für Firmen-SSO; Auth für die Web-UI kommt spätestens in Phase 5, bevor das System über localhost hinaus erreichbar ist.

## Konsequenzen

- Jede Integration wird nur einmal gebaut (MCP), neue Plugins brauchen einen Ordner mit Manifest und einen Container.
- Das `mcp`-SDK ist in Version 2.x (u. a. `MCPServer` statt `FastMCP`); Updates müssen gegen die Migrationshinweise des SDK geprüft werden.
