# Entscheidungen

Kurz festhalten: Was wurde entschieden, warum? Neueste oben.

| Datum | Entscheidung | Begründung |
|---|---|---|
| 2026-10-04 | Neue Pakete im Plugin `action-invoice`: `sqlalchemy` (ORM, parametrisiertes SQL), `jinja2` (Template mit Autoescape), `weasyprint` (PDF, braucht Pango), `pydantic`, `pydantic-settings`, dev: `pytest`, `mypy`; Frontend dev: `vitest` | Playbook-Standardstack (SQLAlchemy, Pydantic); Jinja2/WeasyPrint laut Projektplan 3.4; vitest testet die UI-Logik. Namen und Maintainer über `uv add`/`npm view` geprüft, `pip-audit` und `npm audit --omit=dev` ohne Funde |
| 2026-10-04 | Abweichung vom Plan: keine Tool-`preview_invoice`; die Vorschau zeigt das UI aus den serverseitig berechneten Werten des gespeicherten Entwurfs | Ein PDF-Entwurf ohne Nummer wäre irreführend; das endgültige PDF entsteht erst beim Ausstellen |
| 2026-10-04 | Schritte "Ausstellen" und "PDF" in einem Commit | Ausstellen erzeugt das PDF in derselben Transaktion (keine Nummernlücke bei Renderfehlern) |
| 2026-10-04 | CI (`.github/workflows/ci.yml`) prüft nur den Kern; Plugin-Tests und Frontend-Checks laufen über `make test` | Workflows werden laut Playbook nur auf ausdrücklichen Auftrag geändert; Erweiterung als Vorschlag im Phase-1-Bericht |
| 2026-10-04 | Branch `feat/invoices` für Issue #3 | Entspricht AGENTS.md Abschnitt 6, keine Abweichung |
| 2026-10-01 | Akzeptiertes Risiko: `npm audit` meldet 3 Funde (niedrig) für `cookie <0.7.0` in `@sveltejs/kit` (nur Dev-Abhängigkeit, Build-Zeit; die ausgelieferte statische App enthält keinen Server). Vorgeschlagener Fix ist ein Downgrade auf kit 0.0.30. Verantwortlich: Silver; erneut prüfen bis 2026-11-01 | Kein sinnvoller Fix verfügbar; im Laufzeit-Container ist `cookie` nicht enthalten (`npm audit --omit=dev`: 0 Funde) |
| 2026-10-01 | `ruff`-Ausnahme `S101` gilt für `**/tests/**` statt nur `tests/**` | Plugin-Tests liegen in `plugins/<id>/tests/`; gleiche Begründung wie im Playbook (assert in Tests) |
| 2026-10-01 | Caddy lokal statt Traefik/oauth2-proxy; `hub.localhost/api/*` wird zum Kern geroutet (kein CORS nötig) | Projektplan 3.4; SSO erst in Phase 5, siehe ADR-001 |
| 2026-10-01 | Frontend: SvelteKit (`@sveltejs/kit`, `svelte`, `vite`, `typescript`, `svelte-check`, `@sveltejs/adapter-static`, `@sveltejs/vite-plugin-svelte`), erzeugt mit dem offiziellen `sv`-CLI; Auslieferung über `nginxinc/nginx-unprivileged` | Projektplan 3.4; reine SPA, Nicht-Root-Container; Paketnamen und Herkunft (svelte.dev, `adapter-static` Maintainer Rich Harris) geprüft |
| 2026-10-01 | Neue Python-Abhängigkeiten: `pyyaml` (Manifeste, nur `safe_load`), `mcp` 2.x (offizielles MCP-SDK), dev: `types-pyyaml` | Manifeste in YAML laut Projektplan; MCP als Plugin-Protokoll (ADR-001). Existenz auf PyPI beim Installieren über `uv add` verifiziert |
| 2026-10-01 | Branch `1-phase-0-erstellen-des-grundgerüstes` statt `chore/<kurz>` | Branchname kommt vom GitHub-Issue #1; Abweichung von AGENTS.md Abschnitt 6 bewusst akzeptiert |
| 2026-10-01 | Abhängigkeiten: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` (Laufzeit); `ruff`, `mypy`, `pytest`, `httpx`, `pre-commit` (Dev) | Playbook-Standardstack; `httpx` wird vom FastAPI-TestClient benötigt, `pre-commit` für lokale Checks vor dem Commit |
| 2026-10-01 | Python-Paket `src/hub/` statt Struktur `core/`, `plugins/` aus dem Projektplan (3.5) | Playbook-Standard (AGENTS.md Abschnitt 4); Plugins kommen später als Unterordner |
| 2026-10-01 | Schutzstufe 2 | Rechnungen enthalten personenbezogene Kundendaten; im Zweifel die höhere Stufe |
