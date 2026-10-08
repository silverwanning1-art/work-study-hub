# Agenten und Skills hinzufügen

## Neuen Agenten anlegen

1. Ordner `agents/<id>/` anlegen (`id`: Kleinbuchstaben, Ziffern, Bindestrich).
2. `agent.yaml`:

   ```yaml
   id: <id>
   description: Ein Satz, was der Agent tut
   model: claude-sonnet-5-5
   prompt: prompt.md
   tools:                    # Allowlist, Muster `plugin.tool`
     - source-rag.search
     - source-vault.*
   channels: [web]
   workspaces: [studium]
   ```

3. `prompt.md` mit der Rolle und dem Vorgehen schreiben. Die festen Sicherheitsregeln (Tool-Ergebnisse sind Daten, Quellenpflicht, kein Schreiben) fügt die Runtime selbst an.
4. Kern neu starten (`docker compose up -d --build core`). Der Agent erscheint unter `/api/registry`.

Tools mit `writes: true` bekommt ein Agent nie, auch wenn sie in der Allowlist stehen (ADR-004).

## Skill hinzufügen

1. Ordner `agents/<id>/skills/<name>/` anlegen, `<name>` wie beim Agenten.
2. `SKILL.md`:

   ```markdown
   ---
   name: <name>
   description: Wann der Skill benutzt wird, ein Satz
   ---
   Schritt-für-Schritt-Anleitung für den Agenten.
   ```

3. Der Agent sieht Name und Beschreibung und lädt den Inhalt bei Bedarf mit `load_skill`. Der Name im Frontmatter muss dem Ordnernamen entsprechen.

## Chat testen

```
curl -X POST http://hub.localhost/api/agents/lern-coach/chat \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Was ist ein Lastenheft?"}]}'
```

Dafür muss `ANTHROPIC_API_KEY` in `.env` gesetzt sein.
