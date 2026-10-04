# ADR-002: Rechnungsmodell, Unveränderlichkeit und Bestätigungsflow

Datum: 2026-10-04 · Status: angenommen · Issue: #3

## Kontext

Phase 1 erzeugt steuerlich relevante Dokumente mit personenbezogenen Daten. Ausgestellte Rechnungen dürfen sich nie ändern, Nummern müssen lückenlos und eindeutig sein, und schreibende Aktionen brauchen eine Bestätigung (Projektplan, Abschnitte 4 und 5).

## Entscheidung

- **Plugin `action-invoice`** (MCP-Server) mit eigenem SQLite im Docker-Volume `invoice-data`. Kein Datenbankserver: ein Nutzer, geringe Last (stufen.md). Tabellen entstehen per `create_all`; für spätere Schemaänderungen ist ein Migrationswerkzeug (z. B. Alembic) einzuführen, bevor sich ein Schema ändert.
- **Geld** als ganzzahlige Cent, Mengen in Tausendsteln, nie `float`. Rundung kaufmännisch (weg von null). Die Netto-Beträge werden je Position gerundet, die Steuer je Steuersatz auf der Summe der Nettobeträge.
- **Ausstellen** läuft in einer Transaktion unter einem Prozess-Lock: Pflichtangaben prüfen, Nummer `JJJJ-NNNN` aus `number_counter` (je Jahr fortlaufend) vergeben, Aussteller, Empfänger und Positionen als **Snapshot** (JSON) einfrieren, PDF aus dem Snapshot rendern, Status `issued`. Scheitert ein Schritt (auch das PDF), rollt alles zurück und es entsteht keine Nummernlücke. Eine Unique-Constraint auf der Nummer ist das Sicherheitsnetz.
- **Unveränderlich:** Der Service lehnt Änderungen an nicht-Entwürfen ab. Zusätzlich verbietet ein `before_flush`-Guard jede ORM-Änderung an ausgestellten Rechnungen und ihren Positionen (erlaubt: nur `status` und `paid_on`). Angezeigt und gedruckt wird immer der Snapshot, spätere Stammdatenänderungen wirken sich nicht aus.
- **Storno** nur per Stornorechnung (eigene Nummer, negative Mengen, Daten aus dem Snapshot des Originals, Verweis auf die Originalnummer). Entwürfe dürfen gelöscht werden, ausgestellte Rechnungen nie.
- **Umsatzsteuer:** 19 % oder 7 % je Position. Ein Hinweistext in den Stammdaten schaltet auf 0 % mit diesem Text (Steuerbefreiung, §19 UStG o. ä.). Die steuerliche Richtigkeit liegt bei Silver (Steuerberater/Finanzamt).
- **Bestätigungsflow im Kern:** Schreibende Tools (`writes: true`) werden vom Kern nicht ausgeführt. `POST …/call` liefert `202` mit einer einmaligen, 5 Minuten gültigen `confirmation_id`; erst `POST /api/confirmations/{id}/confirm` führt den Aufruf mit den serverseitig gespeicherten Argumenten aus. Im Gegensatz zum Entwurf (frei änderbar, `writes: false`) gilt das für Ausstellen, Bezahlt und Stornieren.
- **Export:** Das Protokoll `InvoiceExporter` kapselt die Ausgabe. Es gibt nur `PdfExporter` (Jinja2 mit Autoescape + WeasyPrint, kein Zugriff auf externe URLs). XRechnung/ZUGFeRD wird später als weitere Implementierung auf Basis des Snapshots ergänzt.
- Fehlermeldungen des Plugins werden nur für erwartete Fachfehler (`InvoiceError` → `ToolError`) an die UI gegeben; alles andere bleibt intern (MCPServer maskiert es).

## Konsequenzen

- Das PDF wird beim Ausstellen gespeichert und danach nur ausgeliefert, nie neu erzeugt.
- WeasyPrint braucht native Bibliotheken (Pango). Im Container sind sie installiert; lokal für die PDF-Tests `brew install pango`, sonst werden diese Tests mit Begründung übersprungen.
- Der Bestätigungsspeicher des Kerns liegt im Arbeitsspeicher; ein Neustart des Kerns verwirft offene Bestätigungen (die UI fragt dann erneut).
