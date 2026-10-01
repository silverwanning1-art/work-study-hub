---
tags: [projekt, hub, friday, plan]
status: geplant
date: 2026-10-01
---

# Hub-System – Projektplan für Claude Code

> **Arbeitstitel:** `hub` (Name kann sich ändern)
> **Zweck dieses Dokuments:** Übergabe an Claude Code. Zusammen mit dem **Playbook** setzt Claude Code damit das Projekt auf.

---

## 0. Anweisungen an Claude Code (zuerst lesen)

1. **Lies zuerst das Playbook vollständig.** Es regelt das *Wie*: Arbeitsweise, Sicherheitscheck, Commit-Regeln, Branching, Tests, Doku.
2. **Dieses Dokument regelt das *Was*:** Ziele, Architektur, Umfang, Reihenfolge, Abnahmekriterien.
3. **Bei Konflikten:** Bei Prozessfragen gilt das Playbook, bei Inhalts- und Architekturfragen gilt dieses Dokument. Echte Widersprüche nicht still auflösen, sondern Silver fragen.
4. **Arbeite phasenweise.** Nach jeder Phase stoppen und zusammenfassen, was gebaut wurde und was offen ist. Auf Freigabe warten. Nicht mehrere Phasen am Stück bauen.
5. **Erste Session = nur Phase 0.** Repo aufsetzen, Playbook-Regeln einrichten, Gerüst bauen, `docker compose up` grün. Danach stoppen.
6. **Bestehende Systeme nicht anfassen**, bis die jeweilige Phase es verlangt. Betrifft den RAG-Server, FRIDAY und den Vault. Erst einbinden (wrappen), nicht umschreiben.
7. **Sprache:** Code, Bezeichner und Commits auf Englisch (falls das Playbook nichts anderes sagt). Doku und Rückfragen an Silver auf Deutsch.

---

## 1. Ziel

Silver will ein persönliches System zum **Studieren und Arbeiten**. Es soll viele Quellen und Agenten in **einer Oberfläche** zusammenführen. Die Kernidee ist eine **Plugin-Architektur**: Jede Fähigkeit ist ein eigenständiges, austauschbares Plugin. Neue Quellen, Agenten und Eingabekanäle kommen hinzu, ohne dass der Kern geändert werden muss.

**Zwei Arbeitsbereiche (Workspaces) in derselben UI:**

| Workspace | Inhalt |
|---|---|
| **Studium** | Lernen. RAG-Chat über alle Vorlesungsskripte, Obsidian-Vault-Ansicht, Goodnotes-Mitschriften, Fragenkataloge, Prüfungs-Countdown |
| **Arbeit** | Freiberufliche Projekte (z. B. REO-Workshop im November): Rechnungen schreiben, technische Konzepte erarbeiten, Output erzeugen (Dokumente, Folien) |

**Ausdrücklich außerhalb des Systems:**
- **BORA.** Keine Firmendaten, kein Firmenkalender, keine Firmen-Accounts. „Arbeit“ meint hier nur freiberufliche Projekte.
- **VS Code / Entwicklung** bleibt getrennt. Das System kann nur Aufgaben an Coding-Agenten *übergeben* (Phase 6).

---

## 2. Ausgangslage (Bestand auf Silvers Mac)

| Bestand | Ort / Details | Rolle im neuen System |
|---|---|---|
| **RAG-Server** | `~/rag_studium/src/`, FastAPI + ChromaDB, ~31k Chunks aus Bachelor- und Master-Skripten, Port **5678**, Endpoint `POST /query {question, top_k}` | Wird als erstes **Source-Plugin** gewrappt (nicht neu geschrieben) |
| **Obsidian-Vault** | `~/rag_studium/WiIng-Vault`, PARA-Struktur, eigene `CLAUDE.md` | Source-Plugin (lesend). Schreiben nur über bestätigte Actions |
| **FRIDAY** | Python-Telegram-Bot: Claude API, Ollama-Fallback, Faster-Whisper, pyttsx3, ChromaDB, Obsidian-Anbindung; optionale API auf Port **8765** (`ENABLE_API=true`) | Wird zum ersten **Agenten** plus **Telegram-Channel** (Phase 3) |
| **Docker MCP Gateway** | Läuft bereits, u. a. mit Obsidian-MCP-Tools | Kann für Vault-Zugriff wiederverwendet werden (prüfen und entscheiden in Phase 2) |
| **Goodnotes-Connector** | Offizieller MCP, **nur schreibend** (Text, SVG, Mermaid). Kann bestehende Notizen nicht lesen | Action-Plugin. Lesen läuft über Auto-Backup (s. Phase 4) |
| **Belegte Ports** | 5173, 5174, 5678, 8000, 8002, 8080, 8765 (siehe Vault: `06-Claude/Host-Port-Übersicht.md`) | **Nicht belegen.** Neue Dienste laufen hinter dem Reverse Proxy |

---

## 3. Architektur

### 3.1 Überblick

```
 Kanäle (Channels)            Kern (core)                       Plugins (je ein Container, MCP-Server)
 ─────────────────            ───────────                       ─────────────────────────────────────
 Web-UI / PWA (Handy) ─┐                                        ┌─ source-rag        (wrappt RAG :5678)
 Telegram ─────────────┼──►  FastAPI                            ├─ source-vault      (Obsidian, read-only)
 Mail (später) ────────┤     • Plugin-Registry                  ├─ source-goodnotes  (Backup-PDF → OCR → Index)
 Sprache (FRIDAY) ─────┘     • Agent-Runtime (Claude API,       ├─ source-calendar   (ICS-Feeds)
                               Ollama-Fallback)                 ├─ action-invoice    (Rechnungen)
                             • Router (Kanal → Agent)           ├─ action-goodnotes  (Goodnotes-Connector)
                             • MCP-Client zu allen Plugins      └─ action-devtask    (Übergabe an Coding-Agenten)
                             • SQLite (Hub-Zustand)
                                    ▲
                     Caddy (Reverse Proxy): hub.localhost, api.localhost, …
```

### 3.2 Die vier Plugin-Typen

| Typ | Aufgabe | Schnittstelle |
|---|---|---|
| **source** | Daten lesen, durchsuchen, ggf. indexieren | MCP-Tools (`search`, `get`, …) und optional MCP-Resources |
| **action** | Etwas in der Welt verändern (Rechnung, Termin, Datei, Task) | MCP-Tools. **Schreibende Tools brauchen eine Bestätigung** (s. Sicherheit) |
| **agent** | Prompt + Modell + erlaubte Tools + Kanäle | Manifest (YAML) + Prompt-Datei. **Kein eigener Container nötig**, läuft in der Agent-Runtime des Kerns |
| **channel** | Ein- und Ausgabe (Web, Telegram, Mail, Sprache) | Adapter im Kern oder eigener Container. Spricht über eine interne Nachrichten-API mit dem Router |

**Grundsatz:** Source- und Action-Plugins sind **MCP-Server** (offizielles MCP-Python-SDK, Transport *Streamable HTTP* zwischen Containern). So lassen sie sich auch aus Claude Desktop und Claude Code direkt nutzen. Jede Integration wird nur einmal gebaut.

### 3.3 Plugin-Manifest (Vorschlag, in Phase 0 festzurren)

Jedes Plugin hat eine `plugin.yaml`:

```yaml
id: action-invoice
type: action            # source | action | agent | channel
version: 0.1.0
description: Rechnungen für freiberufliche Projekte erstellen und verwalten
workspaces: [arbeit]    # studium | arbeit | global
mcp:
  url: http://action-invoice:8000/mcp
tools:
  - name: create_invoice_draft
    writes: false
  - name: issue_invoice     # vergibt Nummer, erzeugt PDF, danach unveränderlich
    writes: true
    requires_confirmation: true
secrets: [ ]            # Namen der benötigten Secrets, nie Werte
```

Agent-Manifest (`agents/<name>/agent.yaml`):

```yaml
id: friday
description: Alltagsassistent für Termine, Notizen, schnelle Fragen
model: claude-…          # konfigurierbar, Fallback: ollama/<modell>
prompt: prompt.md
tools:                   # Allowlist, Muster erlaubt
  - source-vault.*
  - source-rag.search
  - source-calendar.*
channels: [telegram, web]
workspaces: [global]
```

Der Kern liest beim Start alle Manifeste ein, prüft sie gegen ein Schema (z. B. Pydantic) und zeigt sie in der UI an. **Einen neuen Agenten anlegen heißt: Ordner mit `agent.yaml` und `prompt.md` hinzufügen. Kein Code.**

### 3.4 Tech-Stack (Vorschlag, Playbook kann abweichen)

| Bereich | Wahl | Begründung |
|---|---|---|
| Kern und Plugins | Python 3.12, FastAPI, offizielles `mcp`-SDK, Pydantic | Passt zu FRIDAY und dem RAG-Server, Silver kennt den Stack |
| LLM | Anthropic SDK (Claude), Ollama als Fallback | Wie bei FRIDAY |
| Hub-Zustand | SQLite (Volume) | Reicht für eine Person, leicht umzuziehen |
| Vektor-DB | Bestehendes ChromaDB über `source-rag` | Nicht duplizieren |
| Frontend | SvelteKit + TypeScript als **PWA** | Läuft am Mac und auf dem Handy; leichtgewichtig |
| Reverse Proxy | Caddy | `*.localhost`-Routing ohne Portchaos, später automatisches HTTPS |
| PDF (Rechnungen) | HTML-Template → WeasyPrint (alternativ Typst) | Gut testbar; ZUGFeRD/XRechnung später über `factur-x` ergänzbar |
| Orchestrierung | `docker compose` | Startet auf dem Mac, später ohne Codeänderung auf einem eigenen Server oder in der Cloud |

### 3.5 Repo-Struktur (Vorschlag)

```
hub/
├── CLAUDE.md                 # aus Playbook + Projektkontext
├── README.md
├── docker-compose.yml
├── compose.override.example.yml
├── .env.example              # alle Variablen, keine Werte
├── Caddyfile
├── core/                     # FastAPI: Registry, Router, Agent-Runtime, MCP-Client
├── frontend/                 # SvelteKit-PWA, Workspaces „Studium“ und „Arbeit“
├── plugins/
│   ├── source-rag/
│   ├── source-vault/
│   ├── source-goodnotes/
│   ├── source-calendar/
│   ├── action-invoice/
│   ├── action-goodnotes/
│   └── action-devtask/
├── agents/
│   ├── friday/
│   ├── lern-coach/
│   └── konzept/
├── channels/
│   └── telegram/
├── schemas/                  # JSON-Schema/Pydantic für Manifeste
├── docs/                     # ADRs (Architekturentscheidungen), Plugin-Anleitung
└── tests/
```

### 3.6 Betrieb und Umzugsfähigkeit

- **Alles in Containern.** Der Kern, jedes Plugin, das Frontend und Caddy laufen jeweils in einem eigenen Container.
- **Keine festen Pfade im Code.** Vault, Goodnotes-Backup-Ordner und RAG-URL kommen aus `.env`. Auf dem Mac sind sie Bind-Mounts, auf einem Server Volumes.
- **Der RAG-Server läuft vorerst weiter auf dem Host** (:5678). `source-rag` erreicht ihn über `host.docker.internal`. Ihn selbst zu containerisieren ist eine spätere, eigene Aufgabe.
- **Netzwerk:** Standardmäßig nur `127.0.0.1` binden. Zugriff vom Handy erst ab Phase 5, dann über Tailscale, nicht über offene Ports.
- `make up` / `make down` / `make logs` / `make test` (oder entsprechende Skripte) als einheitlicher Einstieg.

---

## 4. Sicherheit (ergänzend zum Sicherheitscheck des Playbooks)

1. **Secrets:** Nur in `.env` bzw. Docker Secrets, nie im Repo. `.env.example` mit Platzhaltern. Secret-Scan vor jedem Commit (laut Playbook).
2. **Least Privilege:** Vault und Goodnotes-Ordner werden **read-only** gemountet. Ausnahme: Eine Action schreibt ausdrücklich, dann nur in einen definierten Unterordner.
3. **Tool-Allowlist pro Agent.** Ein Agent sieht nur die Tools aus seinem Manifest.
4. **Schreibende Tools brauchen eine Bestätigung** (`requires_confirmation`). Die UI oder der Kanal fragt nach, bevor ausgeführt wird. Für Rechnungen gilt das immer.
5. **Kanal-Eingaben sind nicht vertrauenswürdig.** Mail und Telegram können Prompt-Injection enthalten. Telegram nur für Silvers User-ID (Allowlist). Mail-Inhalte werden als Daten behandelt, nie als Anweisungen.
6. **Personenbezogene Daten** (Rechnungsempfänger, Adressen, Steuernummer) liegen nur im SQLite-Volume bzw. in `data/`. Dieser Ordner ist in `.gitignore`.
7. **Keine BORA-Daten**, auch nicht testweise.
8. **Auth für die Web-UI** spätestens bevor das System außerhalb von localhost erreichbar ist (Phase 5).

---

## 5. Phasen mit Abnahmekriterien

> Reihenfolge begründet: Die **Rechnung hat eine echte Deadline** (REO-Workshop im November). Deshalb kommt `action-invoice` direkt nach dem Fundament. Das ist zugleich ein kleiner, realer Test des Playbooks.

### Phase 0 – Fundament (erste Session)
- Repo anlegen, Playbook-Regeln einrichten: `CLAUDE.md`, Commit-Konvention, Sicherheitscheck, Pre-Commit-Hooks, Linting/Formatierung, Test-Setup.
- `docker-compose.yml` mit `caddy`, `core` (nur Health-Endpoint und Registry, die leere Manifeste lädt) und `frontend` (leere Shell mit Umschalter Studium/Arbeit).
- Manifest-Schemas für Plugin und Agent; ein Beispiel-Plugin `source-hello` als MCP-Server, das der Kern erkennt und aufrufen kann.
- ADR-001: Plugin-Architektur und MCP als Plugin-Protokoll.

**Fertig, wenn:** `docker compose up` startet alles ohne Fehler; `http://hub.localhost` zeigt die Shell; der Kern listet `source-hello` und ruft dessen Tool erfolgreich auf; Tests und Sicherheitscheck laufen grün; keine bestehenden Ports belegt.

### Phase 1 – Rechnungen (`action-invoice`) + Arbeits-Workspace (Ziel: vor dem Workshop)
- Datenmodell: eigene Stammdaten (Name, Anschrift, Steuernummer, Bankverbindung, Kleinunternehmer ja/nein), Kunden, Projekte, Rechnungen, Positionen.
- **Pflichtangaben nach §14 UStG:** vollständiger Name und Anschrift von Leistendem und Empfänger, Steuernummer (oder USt-IdNr.), Ausstellungsdatum, **fortlaufende, einmalig vergebene Rechnungsnummer**, Menge und Art der Leistung, Leistungszeitpunkt bzw. -zeitraum, Entgelt, Steuersatz und -betrag **oder** Hinweis auf Steuerbefreiung bzw. §19 UStG (Kleinunternehmer).
- Ablauf: **Entwurf** (frei änderbar) → **ausstellen** (Nummer vergeben, PDF erzeugen, danach unveränderlich) → **bezahlt** / **storniert** (Storno nur per Stornorechnung, nie durch Löschen).
- PDF-Template, sauber und schlicht, Deutsch.
- UI im Workspace „Arbeit“: Rechnungsliste, Entwurf anlegen, Vorschau, ausstellen (mit Bestätigung), PDF herunterladen.
- Export-Schnittstelle so vorbereiten, dass ZUGFeRD/XRechnung später ergänzt werden kann (nicht jetzt bauen).

**Fertig, wenn:** Eine Rechnung an REO lässt sich vollständig in der UI erstellen und als PDF ausstellen; Nummern sind lückenlos und eindeutig (Test); eine ausgestellte Rechnung lässt sich nicht mehr ändern (Test); alle Pflichtfelder werden geprüft (Test). **Hinweis an Silver:** Vorlage einmal von Steuerberater oder Finanzamt-Merkblatt gegenprüfen lassen.

### Phase 2 – Studium-Workspace
- `source-rag`: MCP-Wrapper um den bestehenden RAG-Server (`search(question, top_k)`, Rückgabe mit `source_path` und Seite).
- `source-vault`: Lesen und Suchen im Vault. **Entscheidung (ADR):** eigener Server oder vorhandenen Docker-MCP-Obsidian-Server wiederverwenden.
- Agent `lern-coach`: nutzt RAG und Vault, antwortet mit Quellenangaben `[Quelle: Datei, S. X]`.
- UI: Chat mit Quellen, Vault-Browser (Markdown-Rendering, Links `obsidian://open?...` zum Bearbeiten in Obsidian), Prüfungsübersicht.

**Fertig, wenn:** Eine Fachfrage im Studium-Workspace liefert eine Antwort mit korrekten Quellenverweisen; Vault-Notizen sind durchsuchbar und öffnen in Obsidian.

### Phase 3 – FRIDAY als Agent + Telegram-Channel
- FRIDAYs Logik analysieren und in drei Teile zerlegen: **Agent** (Prompt + Tools), **Channel** (Telegram) und **Plugins** (was bisher fest eingebaut ist).
- Telegram-Adapter mit User-ID-Allowlist; Sprache (Whisper) als Channel-Feature.
- Der alte FRIDAY läuft weiter, bis der neue gleichwertig ist (kein Big Bang).

**Fertig, wenn:** Dieselben Alltagsanfragen funktionieren über Telegram mit dem neuen System; der alte Bot kann abgeschaltet werden.

### Phase 4 – Goodnotes
- `source-goodnotes`: Überwacht den Ordner, in den das Goodnotes-Auto-Backup die PDFs legt; OCR für Handschrift; Indexierung (eigene Collection oder über `source-rag`, per ADR entscheiden); Anzeige der PDFs im Studium-Workspace.
- `action-goodnotes`: Bindet den offiziellen Goodnotes-Connector ein (z. B. „Fragenkatalog/Mindmap zu Skript X in Goodnotes anlegen“).

**Fertig, wenn:** Eine handschriftliche Mitschrift ist per Suche auffindbar, und der Lern-Coach kann eine Zusammenfassung nach Goodnotes schreiben.

### Phase 5 – Kalender + Zugriff vom Handy
- `source-calendar`: Liest ICS-Feeds (Uni, Arbeit/freiberuflich, privat) und zeigt eine gemeinsame Ansicht. **Kein BORA-Kalender.**
- Zugriff vom Handy: Auth für die Web-UI, Tailscale, PWA installierbar.
- Doku: Wie man den Stack auf einen eigenen Server oder in die Cloud umzieht.

### Phase 6 – Übergabe an Coding-Agenten, Mail, weitere Agenten
- `action-devtask`: Erstellt aus einer Aufgabe ein GitHub-Issue mit Label (wird z. B. von einer Claude-Code-GitHub-Action bearbeitet) **oder** schreibt eine Task-Datei in ein lokales Repo. Ansatz per ADR wählen.
- Mail-Channel (IMAP/SMTP), Eingaben strikt als Daten behandeln.
- Agent `konzept`: technische Konzepte erarbeiten, Output als Dokument/Folien.
- Anleitung „Neuen Agenten hinzufügen“ in `docs/`.

---

## 6. Nicht-Ziele (jetzt bewusst nicht)

- Kein eigener Markdown-Editor; Obsidian bleibt der Editor.
- Keine Buchhaltung, keine Steuererklärung, keine Bankanbindung.
- Kein Multi-User-System.
- Kein Umschreiben des RAG-Servers oder von FRIDAY, bevor die jeweilige Phase dran ist.
- Keine BORA-Integration.

---

## 7. Offene Punkte (bei Bedarf Silver fragen)

- Endgültiger Projektname (statt `hub`).
- Wo liegt das Repo, und GitHub ja/nein? (Für Phase 6 relevant.)
- Kleinunternehmerregelung (§19 UStG) ja/nein? Steuernummer vorhanden? (Phase 1)
- Braucht REO eine XRechnung oder reicht ein PDF? (Phase 1)
- In welchen Cloud-Ordner schreibt das Goodnotes-Backup? (Phase 4)
- Welche ICS-Feeds gibt es (TH Rosenheim, privat)? (Phase 5)

---

## 8. Definition of Done (für jede Phase)

- Abnahmekriterien der Phase erfüllt.
- Tests grün, Sicherheitscheck des Playbooks bestanden, keine Secrets im Repo.
- Commits nach Playbook-Konvention.
- README bzw. `docs/` aktualisiert, neue Architekturentscheidungen als ADR festgehalten.
- Kurze Zusammenfassung an Silver: was gebaut wurde, was offen ist, was die nächste Phase braucht.
