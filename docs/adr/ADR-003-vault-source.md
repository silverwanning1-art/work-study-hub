# ADR-003: Obsidian-Vault als eigener read-only MCP-Server

Datum: 2026-10-08 · Status: angenommen

## Kontext

Phase 2 braucht lesenden Zugriff auf den Obsidian-Vault (`~/rag_studium/WiIng-Vault`), damit der Agent `lern-coach` Notizen durchsuchen und zitieren kann. Zur Wahl standen ein eigener Server oder die Wiederverwendung des vorhandenen Obsidian-Servers im Docker MCP Gateway (Projektplan, Phase 2).

## Entscheidung

- `source-vault` ist ein **eigener MCP-Server** (Plugin-Typ `source`, ein Container), wie `source-hello` und `action-invoice` (ADR-001).
- Der Vault wird **read-only** (`:ro`) in den Container gemountet. Der Server kann technisch nichts schreiben.
- Tools: `search(query, limit)`, `read_note(path)`, `list_notes(folder)`. Alle ohne `writes`, daher ohne Bestätigungsflow.
- Pfade werden gegen das Vault-Wurzelverzeichnis aufgelöst und abgelehnt, wenn sie es verlassen (Path Traversal, Symlinks).
- Der Server wird vom Hub direkt über den MCP-Client angesprochen; das Docker MCP Gateway ist nicht beteiligt.

## Konsequenzen

- Kein Laufzeit-Abhängigkeit vom Gateway, volle Kontrolle über Rechte und Rückgabeformat (Quellenangaben).
- Mehr Eigenbau als bei Wiederverwendung (Suche und Markdown-Parsing selbst pflegen).
- Schreiben in den Vault bleibt außerhalb dieses Plugins; es wäre ein getrenntes `action`-Plugin mit Bestätigung.
