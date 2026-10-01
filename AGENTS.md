# AGENTS.md – Arbeitsweise für KI-Coding-Agents

> Verbindlich für alle KI-Agents in diesem Repo (Claude Code, Codex, GitHub Copilot).
> Dies ist der Kern. Details stehen in `docs/playbook/` und werden bei Bedarf gelesen.

## 0. Verbindlichkeit

- **MUSS / NIEMALS** = harte Regel. **SOLL** = Standard; Abweichung nur mit Begründung.
- Bei Konflikten gilt: ausdrückliche Anweisung des Nutzers > dieses Playbook > eigene Präferenzen.
- Ausnahme: Security-Regeln (Abschnitt 5) werden nur nach ausdrücklicher Bestätigung gebrochen, und der Verstoß wird im Ergebnis klar benannt.

## 1. Projektkontext (beim Projektstart ausfüllen)

- **Zweck:** Persönliches System zum Studieren und Arbeiten (Plugin-Architektur): führt RAG, Obsidian-Vault, Agenten und Rechnungen für freiberufliche Projekte in einer Oberfläche zusammen, für Silver.
- **Schutzstufe:** `STUFE 2` → Regeln je Stufe: `docs/playbook/stufen.md`
- **Owner:** Silver, keine Vertretung
- **Daten:** Ja, personenbezogen (Rechnungsempfänger, Adressen, Steuernummer). Nur im gitignorierten `data/`-Ordner bzw. SQLite-Volume, nie im Repo.
- **Compliance-Rahmen:** keiner

Fehlen diese Angaben, frage zuerst danach.

## 2. Arbeitsweise

- **Erst planen, dann bauen.** Vor jeder nicht-trivialen Änderung einen kurzen Plan vorlegen: Ziel, betroffene Dateien, Vorgehen, offene Fragen. Ab Stufe 2 auf Bestätigung warten.
- **Kleine Schritte.** Eine logische Änderung nach der anderen; nach jedem Schritt lauffähiger Zustand.
- **Nachfragen statt raten**, wenn Anforderungen, Fachregeln oder Datenstrukturen unklar sind.
- **Nur den Auftrag umsetzen.** Kein ungefragtes Refactoring, keine Zusatzfeatures. Auffälligkeiten melden statt nebenbei ändern.
- **Erst lesen, dann schreiben.** Bestehenden Code und Muster ansehen und übernehmen.
- **Nichts erfinden.** Keine ausgedachten APIs, Pakete, Parameter oder Konfigurationswerte. Im Zweifel prüfen oder nachfragen.
- **Ehrlich berichten.** Sagen, was getestet wurde und was nicht. NIEMALS behaupten, Tests oder Checks seien gelaufen, wenn sie nicht tatsächlich ausgeführt wurden.

## 3. Tech-Stack (Standard)

| Bereich | Standard |
|---|---|
| Sprache | Python 3.12+ |
| Pakete & Umgebung | `uv`, alles in `pyproject.toml`, Lockfile `uv.lock` committen |
| Linting & Formatierung | `ruff` (check + format) |
| Typprüfung | `mypy` |
| Tests | `pytest` |
| Web-API | FastAPI |
| Validierung & Konfiguration | Pydantic v2, `pydantic-settings` |
| Datenbank | SQLite lokal, PostgreSQL ab Stufe 2; SQLAlchemy 2.x |
| HTTP-Client | `httpx` (immer mit Timeout) |
| Logging | Standardbibliothek `logging`, Ausgabe nach stdout |

**Abhängigkeiten:** Standardbibliothek vor Fremdpaket. Neue Pakete nur, wenn nötig, mit kurzer Begründung, nur etablierte und gepflegte Pakete. Den Paketnamen exakt prüfen (Tippfehler- und Fake-Pakete sind ein bekannter Angriffsweg).

## 4. Projektstruktur & Befehle

```
src/<paket>/        # Anwendungscode
tests/              # pytest-Tests, Struktur spiegelt src/
docs/               # Doku, Entscheidungen, Playbook-Details
pyproject.toml
uv.lock
.env.example        # alle Umgebungsvariablen mit Platzhaltern
Dockerfile          # ab Stufe 2, Vorlage: docs/playbook/hosting.md
README.md
```

| Zweck | Befehl |
|---|---|
| Installieren | `uv sync` |
| Formatieren & Linten | `uv run ruff format . && uv run ruff check . --fix` |
| Typen prüfen | `uv run mypy src` |
| Testen | `uv run pytest` |

Vor jedem Commit MÜSSEN Format, Lint, Typprüfung und Tests grün sein.

## 5. Security (NIEMALS verhandelbar)

- **NIEMALS Secrets** (API-Keys, Passwörter, Tokens, Connection-Strings) in Code, Tests, Logs oder Commits. Konfiguration nur über Umgebungsvariablen; jede neue Variable mit Platzhalter in `.env.example`.
- **NIEMALS echte personenbezogene Daten** in Code, Tests, Fixtures oder Beispieldateien. Nur synthetische Testdaten.
- **Alle externen Eingaben validieren** (Pydantic-Modelle für Requests, Dateien, Umgebungsvariablen).
- **SQL nur parametrisiert** bzw. über das ORM, nie per String-Zusammenbau.
- **Verboten:** `eval`/`exec`, `pickle` mit fremden Daten, `subprocess` mit `shell=True` und Eingaben, `yaml.load` (stattdessen `yaml.safe_load`).
- **Keine eigene Authentifizierung oder Passwortspeicherung.** Login kommt über SSO/Proxy (`docs/playbook/hosting.md`).
- **Sicherheitschecks NIEMALS ausschalten** (`# nosec`, `# noqa` für Security-Regeln, `--no-verify`, CI-Schritte überspringen) ohne ausdrückliche Rückfrage.
- **Fehlermeldungen an Nutzer** ohne Stacktraces oder interne Details.
- **Secret gefunden?** Sofort stoppen und den Nutzer informieren: Das Secret muss rotiert werden, Löschen aus der Historie reicht nicht.

Details: `docs/playbook/security.md`

## 6. Git-Workflow

- **NIEMALS direkt auf `main`.** Branches: `feat/<kurz>`, `fix/<kurz>`, `chore/<kurz>`, `docs/<kurz>`.
- **Conventional Commits** auf Englisch, im Imperativ: `feat: add CSV export for orders`
- Committen nur mit grünen Checks. Ein Commit = eine logische Änderung.
- **Verboten:** Force-Push, Umschreiben geteilter Historie, `--no-verify`.
- **Push und Pull Request nur auf Anweisung.** Mergen macht NIEMALS der Agent.
- PRs nutzen die Vorlage `.github/pull_request_template.md`.

Details: `docs/playbook/git-workflow.md`

## 6a. Nachvollziehbarkeit (ab Stufe 2)

- Jede Änderung hat ein **Issue**; Commits (`Refs: #<nr>`) und PR verweisen darauf.
- **Autor ≠ Reviewer.** Ein KI-Agent zählt nie als Reviewer oder Freigeber.
- PR enthält Risikoeinstufung und offengelegte KI-Beteiligung.
- Branch-Schutz, CODEOWNERS, CI-Checks und Nachweise (Issues, PRs, Logs) werden NIEMALS umgangen, geändert oder gelöscht.

Details und Zuordnung zu ISO 27001, SOC 2, NIS2: `docs/playbook/compliance.md`

## 7. Code-Qualität

- Type Hints überall; Docstrings (Google-Stil) für öffentliche Funktionen und Klassen.
- Code, Bezeichner und Commits auf Englisch. Kommentare erklären das *Warum*, nicht das *Was*.
- Kleine Funktionen mit einer Aufgabe, sprechende Namen.
- Spezifische Exceptions, kein nacktes `except:`, Fehler nie stillschweigend schlucken.
- `logging` statt `print`. Keine personenbezogenen Daten oder Secrets in Logs.
- **Tests:** Jede neue Fachlogik bekommt Tests. Bei Bugfixes zuerst einen Test schreiben, der den Fehler reproduziert. Tests laufen ohne Netzwerk und ohne externe Systeme (mocken).
- Kein toter oder auskommentierter Code, keine TODOs ohne Erklärung.

## 8. Betrieb

- Konfiguration ausschließlich über Umgebungsvariablen.
- Web-Apps haben einen Endpoint `GET /health`, der `{"status": "ok"}` liefert.
- Logs nach stdout, keine Logdateien im Container.
- Container nach Vorlage in `docs/playbook/hosting.md`.

## 9. Dokumentation

- `README.md` aktuell halten: Zweck, Setup, Start, Umgebungsvariablen, Tests.
- Wichtige Entscheidungen (Architektur, Pakete, Abweichungen vom Playbook) kurz in `docs/decisions.md` festhalten: Datum, Entscheidung, Begründung.

## 10. Definition of Done

Am Ende jeder Aufgabe diese Liste prüfen und das Ergebnis berichten:

- [ ] Auftrag erfüllt, nichts darüber hinaus
- [ ] Format, Lint, Typprüfung und Tests grün (tatsächlich ausgeführt)
- [ ] Neue Logik ist getestet
- [ ] Keine Secrets, keine echten personenbezogenen Daten
- [ ] `.env.example` und `README.md` aktuell
- [ ] Neue Abhängigkeiten begründet
- [ ] Ab Stufe 2: Issue verknüpft, Risiko eingeschätzt
- [ ] Zusammenfassung an den Nutzer: was geändert wurde, wie getestet, offene Punkte, Risiken

## 11. Playbook weiterentwickeln

Korrigiert der Nutzer etwas, das als allgemeine Regel taugt, schlage vor, es hier zu ergänzen. Dieses Playbook nur nach Zustimmung ändern.
