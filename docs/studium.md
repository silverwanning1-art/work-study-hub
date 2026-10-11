# Studium-Workspace

Stand: Phase 2 (Lern-Coach, Karteikarten, Prof-Profile, Probeprüfungen). Aufruf: `http://hub.localhost/studium`.

## Überblick

| Seite | Zweck |
|---|---|
| `/studium/chat` | Chat mit dem Agenten `lern-coach`; Antworten mit Quellen (`[Quelle: Datei, S. X]`), Links öffnen Notizen in Obsidian |
| `/studium/vault` | Vault durchsuchen und Notizen lesen (nur lesend) |
| `/studium/karteikarten` | Stapel, Fälligkeiten, Statistik, Karten aus einem Thema erzeugen |
| `/studium/karteikarten/lernen` | Lernmodus: Vorderseite, aufdecken, bewerten (nochmal, schwer, gut, leicht) |
| `/studium/profile` | Prof-Profile anlegen und bearbeiten |
| `/studium/pruefungen` | Prüfungen auflisten, neue im Stil eines Profs erzeugen |
| `/studium/pruefungen/durchfuehren` | Prüfung bearbeiten (ohne Timer) |
| `/studium/pruefungen/ergebnis` | Punkte je Thema, Detailansicht, schwache Themen als Karteikarten |

Voraussetzungen: Stack läuft (`make up`), `ANTHROPIC_API_KEY` in `.env` (siehe README), der RAG-Server läuft auf dem Host (`127.0.0.1:5678`) und der Vault liegt unter `VAULT_DIR`. Die Chat-Funktionen (Chat, Karten erzeugen, Prüfung erzeugen, Bewertung durch das Modell) kosten API-Guthaben; Vault, Lernen und Selbstbewertung nicht.

## Bausteine

```
Browser ──> Caddy ──> Kern (FastAPI) ──MCP──> source-rag     ──> RAG-Server (Host :5678)
                          │            ├────> source-vault   ──> Vault (:ro)
                          │            └────> action-study   ──> Volume study-data (SQLite)
                          └── Agent-Runtime ──> Claude API (lern-coach)
```

- **source-rag:** Tool `search`, umhüllt den RAG-Server (unverändert). Liefert Treffer mit fertigem `citation`.
- **source-vault:** Tools `search`, `read_note`, `list_notes`. Container mit `read_only`, `cap_drop: ALL` und Vault-Mount `:ro`; versteckte Ordner, Symlinks und Pfade außerhalb des Vaults sind nie lesbar (ADR-003).
- **action-study:** Karteikarten, Lernfortschritt, Prof-Profile, Prüfungen und Durchführungen in SQLite (Volume `study-data`).
- **lern-coach:** Agent mit den Tools von `source-rag` und `source-vault` und drei Skills (siehe unten). Er hat keinen Zugriff auf `action-study`; das erzwingt ein Test.

## Datenschutz

Karten, Fortschritt, Profile, Prüfungen und Antworten bleiben im Volume `study-data`. An die Claude API gehen nur der Chat-Verlauf, Tool-Ergebnisse (Skriptauszüge, Notizen) und, bei der Bewertung, deine Antworten samt Musterlösung. Daten des Arbeitgebers gehören nicht in den Hub.

## Karteikarten

1. Im Generieren-Dialog Thema oder Skript angeben. Der Skill `karteikarten-erstellen` sucht passende Stellen und liefert einen **Entwurf** mit Quellenangabe je Karte.
2. Entwurf prüfen, Karten streichen oder ändern, speichern (mit Bestätigungsdialog, `save_cards`).
3. Lernen: Karten, die heute oder früher fällig sind. Die Bewertung plant die nächste Wiederholung (SM-2-artig, nur ganzzahlige Rechnung, höchstens 365 Tage; `scheduling.py`).

Bekannte Grenzen: Wer denselben Entwurf zweimal speichert, bekommt Dubletten. Es gibt keinen Import und keinen Export.

## Prüfungen im Stil eines Profs

1. **Profil** anlegen: Beschreibung, Fragestil, Anteile von Multiple Choice, offenen Fragen und Rechenaufgaben (Summe 100), Schwierigkeit, Besonderheiten.
2. **Erzeugen:** Der Skill `pruefung-nach-prof-profil` sucht Altklausuren und Musterfragen im RAG-Index, leitet daraus den Stil ab und erzeugt einen Entwurf mit Musterlösungen und Quellen. Altklausuren werden nicht wörtlich kopiert. Bei Multiple Choice muss die Musterlösung wortgleich einer Option entsprechen.
3. **Prüfen und speichern** (mit Bestätigung, `save_exam`).
4. **Durchführen**, ohne Timer:
   - *Schreiben:* Antworten tippen. Multiple Choice wird lokal bewertet, offene Fragen bewertet der Lern-Coach (Skill `antworten-bewerten`) in Stapeln.
   - *Abfragen:* Antwort aufdecken und sich selbst bewerten (falsch, teilweise, richtig).
5. **Ergebnis:** Punkte je Thema. KI-Punkte haben Vorrang vor der Selbstbewertung. Bei schwachen Themen führt ein Link zum Karteikarten-Generator mit vorbelegtem Thema.

Die Oberfläche ruft für Erzeugung und Bewertung den Chat-Endpoint des Agenten auf, prüft die Antwort (Schema, Punkte höchstens wie in der Frage) und speichert über die Plugin-Tools. Das Plugin lehnt zu hohe Punkte ab und speichert alles oder nichts.

## Sicherheitsregeln

- **Agenten schreiben nie** (ADR-004): Tools mit `writes: true` werden dem Modell nicht angeboten. Gespeichert wird nur über die Oberfläche.
- **Bestätigung nötig:** `save_cards`, `delete_deck`, `save_exam`, `delete_exam`, `delete_profile`.
- **Ohne Bestätigung** (Ausnahme in ADR-004, persönlicher Lernzustand, in keiner Agent-Allowlist): `rate_card`, `save_profile`, `start_attempt`, `save_answer`, `save_grading` sowie alle lesenden Tools.
- **Tool-Ergebnisse sind Daten, keine Anweisungen.** Das gilt auch für Altklausuren und Profilbeschreibungen: Ein Profil beeinflusst nur Stil und Gewichtung.
- Der API-Key liegt nur in `.env` und wird nie geloggt.

## Tools von action-study

| Bereich | Lesend | Schreibend |
|---|---|---|
| Karten | `list_decks`, `list_cards`, `get_due_cards`, `get_stats` | `rate_card`, `save_cards` (Bestätigung), `delete_deck` (Bestätigung) |
| Profile | `list_profiles` | `save_profile`, `delete_profile` (Bestätigung) |
| Prüfungen | `list_exams`, `get_exam`, `list_attempts`, `get_attempt` | `save_exam` (Bestätigung), `delete_exam` (Bestätigung), `start_attempt`, `save_answer`, `save_grading` |

Datenmodell: `Deck`, `Card` (mit Lernzustand), `ReviewLog`, `ProfProfile`, `Exam`, `ExamQuestion`, `ExamAttempt`, `AttemptAnswer` (`models.py`). Beim Start legt das Plugin fehlende Tabellen an; es gibt noch keine Migrationen. Ändert sich eine bestehende Tabelle, ist dafür eine Migration nötig.

## Fehlersuche

| Symptom | Ursache und Abhilfe |
|---|---|
| Chat antwortet `503` | `ANTHROPIC_API_KEY` fehlt in `.env`; danach `docker compose up -d core` |
| Chat-Fehler, Log `credit balance is too low` | Guthaben bei Anthropic aufladen (`docker compose logs core`) |
| Keine Treffer aus Skripten | RAG-Server läuft nicht auf `127.0.0.1:5678` oder `source-rag` erreicht den Host nicht (`RAG_URL`) |
| Vault leer | `VAULT_DIR` zeigt auf den falschen Ordner; der Mount ist nur lesend |
| Neue Seiten fehlen | Frontend neu bauen: `docker compose up -d --build frontend` |

## Nicht Teil von Phase 2

Orchestrator (ein Agent ruft andere per `ask_agent`), FRIDAY als Agent und Telegram (Phase 3), PDF-Export von Prüfungen, Streaming der Chat-Antworten, Ollama-Fallback.
