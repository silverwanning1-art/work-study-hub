# Entscheidungen

Kurz festhalten: Was wurde entschieden, warum? Neueste oben.

| Datum | Entscheidung | Begründung |
|---|---|---|
| 2026-10-01 | Branch `1-phase-0-erstellen-des-grundgerüstes` statt `chore/<kurz>` | Branchname kommt vom GitHub-Issue #1; Abweichung von AGENTS.md Abschnitt 6 bewusst akzeptiert |
| 2026-10-01 | Abhängigkeiten: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` (Laufzeit); `ruff`, `mypy`, `pytest`, `httpx`, `pre-commit` (Dev) | Playbook-Standardstack; `httpx` wird vom FastAPI-TestClient benötigt, `pre-commit` für lokale Checks vor dem Commit |
| 2026-10-01 | Python-Paket `src/hub/` statt Struktur `core/`, `plugins/` aus dem Projektplan (3.5) | Playbook-Standard (AGENTS.md Abschnitt 4); Plugins kommen später als Unterordner |
| 2026-10-01 | Schutzstufe 2 | Rechnungen enthalten personenbezogene Kundendaten; im Zweifel die höhere Stufe |
