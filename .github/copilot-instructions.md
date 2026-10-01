# Anweisungen für GitHub Copilot

Die verbindlichen Regeln für dieses Repo stehen in `AGENTS.md` im Repo-Root. Lies und befolge sie vollständig. Details stehen in `docs/playbook/`.

Die wichtigsten harten Regeln in Kurzform (falls AGENTS.md nicht geladen ist):

- Python 3.12+, `uv`, `ruff`, `mypy`, `pytest`, FastAPI, Pydantic v2.
- Erst Plan vorschlagen, dann in kleinen Schritten umsetzen. Nur den Auftrag umsetzen.
- NIEMALS Secrets oder echte personenbezogene Daten in Code, Tests, Logs oder Commits. Konfiguration nur über Umgebungsvariablen, neue Variablen in `.env.example`.
- Alle externen Eingaben validieren, SQL nur parametrisiert, kein `eval`/`exec`/`pickle`/`shell=True`.
- Keine eigene Authentifizierung; Login kommt über SSO/Proxy.
- NIEMALS direkt auf `main`. Conventional Commits auf Englisch. Mergen macht nie der Agent.
- Ab Stufe 2: jede Änderung mit Issue-Referenz (`Refs: #<nr>`); der Agent ist nie Reviewer oder Freigeber; Branch-Schutz und CI-Checks nie umgehen.
- Type Hints, Tests für neue Logik, keine stillen Exceptions, `logging` statt `print`.
- Nichts erfinden; nie behaupten, Tests seien gelaufen, wenn sie nicht ausgeführt wurden.
