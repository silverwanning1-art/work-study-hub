# ADR-004: Agent-Runtime, Skills und Schreibverbot für Agenten

Datum: 2026-10-08 · Status: angenommen

## Kontext

Der Hub braucht Agenten, die die Tools der Plugins benutzen (Projektplan, 3.3). Der erste ist der `lern-coach`. Agenten verarbeiten Texte aus Skripten und Notizen, die Anweisungen enthalten können (Prompt Injection). Außerdem sollen Agenten erweiterbar sein, ohne den Kern zu ändern.

## Entscheidung

- Die Agent-Runtime (`src/hub/agent_runtime.py`) führt einen begrenzten Tool-Loop aus (höchstens 8 Runden, 4096 Ausgabe-Tokens je Runde). Das Sprachmodell hängt hinter einem kleinen Interface (`src/hub/llm.py`), im Test wird es durch ein Skript ersetzt. Erste Implementierung: Anthropic API. Ein Ollama-Fallback folgt später.
- **Tool-Allowlist:** Der Agent sieht nur Tools, die sein `agent.yaml` per Muster (`plugin.tool`) freigibt und die das Plugin im Manifest deklariert. Alles andere wird abgelehnt und geloggt.
- **Agenten schreiben nie.** Tools mit `writes: true` werden dem Modell nicht angeboten und sind auch bei erfundenen Namen nicht aufrufbar. Schreiben passiert nur durch die UI über den Bestätigungsflow.
- **Tool-Ergebnisse sind Daten.** Der Systemprompt enthält eine feste Regel dazu; sie gilt für jeden Agenten und lässt sich im Agent-Prompt nicht abschalten.
- **Skills:** `agents/<id>/skills/<name>/SKILL.md` mit Frontmatter (`name`, `description`). Namen und Beschreibungen stehen im Systemprompt, den Inhalt lädt das Modell bei Bedarf über das interne Tool `load_skill`. Ein neuer Skill ist ein neuer Ordner, kein Code.
- Der Chat-Endpoint (`POST /api/agents/{id}/chat`) ist zustandslos: die UI sendet den Verlauf (höchstens 40 Nachrichten à 8000 Zeichen), die letzte Nachricht muss vom Nutzer sein.
- Der API-Key kommt aus `ANTHROPIC_API_KEY` (`SecretStr`), nie aus dem Repo. Ohne Key antwortet der Chat mit 503.

## Ausnahme vom Bestätigungsprinzip (Paket 2b/2c, braucht Freigabe)

Tools, die nur den persönlichen Lernzustand fortschreiben, laufen ohne Bestätigungsdialog, weil sonst jede Karte einen Dialog auslöst. Sie sind in `plugin.yaml` als `writes: false` deklariert und stehen in **keiner** Agent-Allowlist.

- Umgesetzt in Paket 2b: `action-study.rate_card` (ändert nur Fälligkeit, Intervall und Faktor einer Karte, schreibt einen Eintrag ins Bewertungsprotokoll).
- Vorgesehen für 2c: `save_answer`.
- Nicht betroffen und weiter mit Bestätigung: alles, was Inhalte anlegt oder löscht (`save_cards`, `delete_deck`).
- Absicherung: ein Test prüft, dass `lern-coach` keine Tools von `action-study` in der Allowlist hat.

## Konsequenzen

- Ein kompromittierter Skriptinhalt kann den Agenten täuschen, aber nichts verändern oder löschen.
- Daten aus Tool-Ergebnissen gehen an die Anthropic API (Prompt und Kontext). Das gilt für Skriptauszüge und Notizen, die der Agent abruft.
- Kosten entstehen pro Anfrage; das Rundenlimit begrenzt sie.
