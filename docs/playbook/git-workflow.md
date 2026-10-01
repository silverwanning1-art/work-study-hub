# Git-Workflow – Details

Ergänzt `AGENTS.md` Abschnitt 6.

## Ablauf einer Aufgabe

1. Aktuellen Stand holen: `git switch main && git pull`
2. Branch anlegen: `git switch -c feat/csv-export`
3. In kleinen Schritten arbeiten; nach jedem logischen Schritt Checks laufen lassen und committen.
4. Vor dem Push: Format, Lint, Typen, Tests grün; `git status` sauber; keine unbeabsichtigten Dateien.
5. Push und PR nur auf Anweisung des Nutzers: `git push -u origin feat/csv-export`
6. PR-Beschreibung nach Vorlage ausfüllen. Review und Merge macht ein Mensch.

## Commit-Nachrichten (Conventional Commits)

Format: `<typ>(<optionaler bereich>): <beschreibung>` – Englisch, Imperativ, klein, ohne Punkt, max. ~72 Zeichen.

| Typ | Wofür |
|---|---|
| `feat` | Neue Funktion |
| `fix` | Fehlerbehebung |
| `refactor` | Umbau ohne Verhaltensänderung |
| `test` | Tests ergänzen/ändern |
| `docs` | Nur Dokumentation |
| `chore` | Build, Abhängigkeiten, Konfiguration |
| `ci` | Pipeline-Änderungen |

Gute Beispiele:

```
feat(orders): add CSV export endpoint
fix: handle empty upload without crashing
chore(deps): bump httpx to 0.28
test(orders): cover rounding of net prices
```

Schlechte Beispiele: `update`, `fixes`, `WIP`, `changed stuff`, `feat: various improvements`.

Bei Bedarf ein Body nach einer Leerzeile: *warum* die Änderung nötig war, nicht *was* geändert wurde (das zeigt der Diff).

Ab Stufe 2 verweist jeder Commit im Footer auf das Issue:

```
feat(orders): add CSV export endpoint

Finance needs monthly exports for reconciliation.

Refs: #42
```

## Was nie committet wird

- `.env`, Zugangsdaten, Zertifikate, private Schlüssel
- Virtuelle Umgebungen (`.venv/`), Caches (`__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`)
- Lokale Datenbanken (`*.sqlite`, `*.db`), Logdateien, Exporte mit echten Daten
- IDE-Einstellungen, die nur für eine Person gelten

## Verboten für den Agent

- Direkte Commits auf `main`
- `git push --force` / `--force-with-lease` auf geteilte Branches
- `git commit --no-verify`, Hooks deaktivieren
- `git rebase` oder `git reset --hard` auf bereits gepushte Commits ohne Rückfrage
- PRs mergen, Branch-Schutz ändern, Releases taggen
- PRs freigeben (auch nicht „im Auftrag“), CODEOWNERS oder CI-Workflows ändern ohne ausdrücklichen Auftrag

## Wenn etwas schiefgeht

- Letzten lokalen Commit verwerfen (noch nicht gepusht): `git reset --soft HEAD~1` und Nutzer informieren.
- Gepushte Änderung zurücknehmen: `git revert <sha>` (neuer Commit, Historie bleibt erhalten).
- Merge-Konflikte: Konflikt erklären, Lösung vorschlagen, nicht blind „ours/theirs“ wählen.
