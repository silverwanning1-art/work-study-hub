# Compliance – Nachweise aus dem Entwicklungsprozess

Ergänzt `AGENTS.md` Abschnitt 6a. Relevant, sobald in `AGENTS.md` Abschnitt 1 ein Compliance-Rahmen eingetragen ist oder Schutzstufe 3 gilt.

## Worum es geht

Rahmenwerke wie **ISO 27001**, **SOC 2** oder **NIS2** zertifizieren keine einzelne App, sondern prüfen, ob eine Organisation ihre Sicherheitskontrollen wirksam betreibt.

- **ISO 27001**: internationale Zertifizierung des Informationssicherheits-Managementsystems (ISMS). Im DACH-Raum der verbreitetste Standard.
- **SOC 2**: Prüfbericht nach US-Standard (AICPA), erstellt von Wirtschaftsprüfern. Type I bewertet das Kontrolldesign zu einem Stichtag, Type II die Wirksamkeit über einen Zeitraum (meist 6–12 Monate). Vor allem relevant für Software- und SaaS-Anbieter mit US-Kunden.
- **NIS2** (in Deutschland: NIS2-Umsetzungsgesetz, in Kraft seit 6. Dezember 2025): gesetzliche Pflicht zu Risikomanagement, Meldewesen und Registrierung für Unternehmen in bestimmten Sektoren ab gesetzlichen Schwellenwerten.

**Was dieses Playbook leistet:** Es sorgt dafür, dass jede Änderung **nachvollziehbar, geprüft und belegt** ist. Diese Spuren (Issues, PRs, Reviews, CI-Logs, Deployments) sind genau die Nachweise, die Auditoren für den Entwicklungsprozess sehen wollen.

**Was es nicht leistet:** Eine Zertifizierung oder ein SOC-2-Bericht erfordert ein Managementsystem der ganzen Organisation (Richtlinien, Risikoanalyse, Zugriffsverwaltung, Schulungen, Lieferantenmanagement, Audit). Das Playbook ist ein Baustein davon, nicht der Ersatz.

## Kernprinzip: Jede Änderung hat eine lückenlose Spur

```
Anforderung (Issue/Ticket)
  → Branch + Commits (verweisen auf Issue)
  → Pull Request (verweist auf Issue, Risiko eingeschätzt)
  → automatische Checks (CI-Log)
  → Review + Freigabe durch eine andere Person
  → Merge
  → Deployment (Image-Tag = Commit-SHA, Zeitpunkt, wer)
```

Ein Auditor muss für jede produktive Änderung beantworten können: **Wer hat sie angefordert, wer gebaut, wer geprüft, wer freigegeben, was wurde getestet, wann ging sie live?**

## Regeln

### Nachvollziehbarkeit

- Jede Änderung ab Stufe 2 beginnt mit einem **Issue/Ticket**, das Ziel und Akzeptanzkriterien beschreibt.
- Commits und PRs **verweisen auf das Issue** (z. B. Commit-Footer `Refs: #42`, PR-Feld „Issue“).
- Entscheidungen mit Sicherheits- oder Architekturbezug stehen in `docs/decisions.md`.
- **KI-Beteiligung wird im PR offengelegt** (Feld in der PR-Vorlage). Verantwortlich für den Code ist immer der Mensch, der den PR stellt.

### Funktionstrennung (Separation of Duties)

- **Autor ≠ Reviewer.** Niemand gibt seinen eigenen PR frei. Ein KI-Agent zählt nie als Reviewer oder Freigeber.
- Ab Stufe 3: Wer Code schreibt, deployt nicht allein in Produktion. Das Deployment läuft über die Pipeline nach Freigabe.
- Pflicht-Reviewer über `.github/CODEOWNERS` für sensible Bereiche (Auth, Konfiguration, CI, Infrastruktur).

### Änderungsmanagement

- Branch-Schutz auf `main`: PR erforderlich, mindestens 1 Freigabe (Stufe 3: 2 oder Code-Owner), alle Checks grün, keine Freigabe durch den Autor, Admins nicht ausgenommen.
- Jeder PR enthält eine **Risikoeinstufung** (niedrig/mittel/hoch) und bei „hoch“ einen Rollback-Plan.
- **Notfall-Änderungen** (Hotfix ohne vollständiges Review): nur durch berechtigte Person, nachträgliches Review innerhalb von 2 Werktagen, Begründung im PR. Der Agent stuft nie selbst etwas als Notfall ein.

### Schwachstellenmanagement

- Dependency- und Secret-Scans laufen automatisch (siehe `security.md`).
- Funde werden als Issue erfasst und nach Schweregrad behoben. Richtwerte: kritisch sofort, hoch innerhalb 30 Tagen, mittel im nächsten regulären Zyklus. Unternehmensinterne Fristen haben Vorrang.
- Akzeptierte Risiken (Fund wird bewusst nicht behoben) werden mit Begründung, Verantwortlichem und Ablaufdatum in `docs/decisions.md` dokumentiert.

### Umgebungen & Zugriff

- Test und Produktion sind getrennt, mit getrennten Zugangsdaten.
- Keine Produktivdaten in Entwicklung oder Test.
- Zugriff auf Repo, Pipeline und Server nach Minimalprinzip; Berechtigungen regelmäßig überprüfen (Aufgabe des Owners, nicht des Agenten).

### Aufbewahrung von Nachweisen

- Issues, PRs, Reviews und CI-Logs werden nicht gelöscht.
- CI-Logs und Deployment-Historie so lange aufbewahren, wie es der Compliance-Rahmen verlangt (bei SOC 2 Type II mindestens über den Prüfzeitraum; Plattform-Standardaufbewahrung prüfen und ggf. verlängern oder exportieren).

## Zuordnung zu Rahmenwerken (Orientierung)

| Playbook-Baustein | ISO 27001:2022 (Anhang A) | SOC 2 (Trust Services Criteria) | NIS2 / BSIG |
|---|---|---|---|
| Sicherer Entwicklungsprozess insgesamt | 8.25 Sicherer Entwicklungslebenszyklus | CC8.1 | Sicherheit bei Erwerb, Entwicklung und Wartung |
| Security-Regeln, sichere Programmierung | 8.28 Sichere Programmierung | CC8.1 | dto. |
| Tests & Security-Scans in der CI | 8.29 Sicherheitstests | CC7.1, CC8.1 | Umgang mit Schwachstellen |
| PR, Review, Freigabe, Branch-Schutz | 8.32 Änderungsmanagement | CC8.1 | dto. |
| Getrennte Umgebungen | 8.31 Trennung von Umgebungen | CC8.1 | dto. |
| Dependency-Scan, Updates | 8.8 Technische Schwachstellen | CC7.1 | Umgang mit Schwachstellen, Lieferkette |
| Secrets-Management | 8.24 Kryptografie / 5.17 Authentisierungsinformationen | CC6.1 | Zugriffskontrolle |
| SSO statt eigener Login | 5.15–5.18 Zugriffssteuerung | CC6.1–CC6.3 | Zugriffskontrolle |
| Logging & Monitoring | 8.15 Protokollierung, 8.16 Überwachung | CC7.2 | Bewältigung von Sicherheitsvorfällen |
| KI-Tools nur freigegeben, keine Firmendaten in Prompts | 5.23 Cloud-Dienste, 8.30 Ausgelagerte Entwicklung | CC9.2 (Lieferanten) | Sicherheit der Lieferkette |

Die Zuordnung ist eine Orientierung für Gespräche mit Informationssicherheit und Auditoren, keine verbindliche Kontrollabdeckung. Die gültige Zuordnung legt das ISMS des Unternehmens fest.

## Für den Agent

- Ohne Issue-Referenz ab Stufe 2 keinen PR vorbereiten, sondern nachfragen.
- Commits mit `Refs: #<nr>` versehen, PR-Vorlage vollständig ausfüllen inkl. Risiko und KI-Beteiligung.
- NIEMALS Branch-Schutz, CODEOWNERS, CI-Checks oder Aufbewahrungseinstellungen ändern oder umgehen.
- NIEMALS einen PR freigeben, mergen oder als Notfall deklarieren.
- Gefundene Schwachstellen melden und als Issue vorschlagen, nicht stillschweigend „mitfixen“ außerhalb des Auftrags.
