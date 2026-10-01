# KI-Coding-Playbook

Regeln, damit KI-Coding-Agents (Claude Code, Codex, GitHub Copilot) nachvollziehbar, sicher und einheitlich arbeiten.

## Verwendung

1. Inhalt dieses Ordners in ein neues Repo kopieren (oder das Repo als Template nutzen).
2. In `AGENTS.md` Abschnitt 1 den Projektkontext ausfüllen, vor allem die **Schutzstufe**.
3. Fertig: Die Tools lesen ihre Datei automatisch.

| Tool | Liest |
|---|---|
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` (bindet `AGENTS.md` per `@AGENTS.md` ein) |
| GitHub Copilot | `.github/copilot-instructions.md` (verweist auf `AGENTS.md`) |

Welche Dateien die Tools lesen, ändert sich gerade häufig – vor Einsatz kurz in der jeweiligen Doku prüfen.

## Aufbau

```
AGENTS.md                         Kern-Playbook (immer geladen, kurz halten)
CLAUDE.md                         Ergänzungen für Claude Code
.github/copilot-instructions.md   Ergänzungen für Copilot
.github/pull_request_template.md  PR-Vorlage
.github/CODEOWNERS                Pflicht-Reviewer (Platzhalter ersetzen)
docs/playbook/stufen.md           Was je Schutzstufe zusätzlich gilt
docs/playbook/security.md         Security-Details, CI-Checks
docs/playbook/git-workflow.md     Branches, Commits, Verbote
docs/playbook/hosting.md          Dockerfile, Compose, SSO, Deployment
docs/playbook/compliance.md       Nachweise für ISO 27001, SOC 2, NIS2
docs/decisions.md                 Entscheidungslog des Projekts
```

## Wichtig

Das Playbook ist **weich**: Die KI hält sich meistens daran, aber nicht garantiert. Alles Kritische muss zusätzlich **hart** in der CI geprüft werden (Vorlage in `docs/playbook/security.md`).

Das Playbook macht kein Unternehmen ISO-27001-zertifiziert oder SOC-2-konform. Es erzeugt die Nachweise, die solche Audits für den Entwicklungsprozess verlangen. Details: `docs/playbook/compliance.md`.

## Weiterentwickeln

Jedes Mal, wenn die KI etwas falsch macht, das als allgemeine Regel taugt: Regel ergänzen. Das Playbook ist eine Sammlung gelernter Lektionen und gehört versioniert in Git.
