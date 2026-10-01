# Schutzstufen

Die Stufe steht in `AGENTS.md` Abschnitt 1. Höhere Stufen erben alle Regeln der niedrigeren.
Im Zweifel die höhere Stufe wählen. Ändert sich Zweck oder Datenlage, Stufe neu prüfen und den Nutzer darauf hinweisen.

## Stufe 1 – persönlich

**Wann:** Nur der Owner nutzt die App, keine Firmen- oder personenbezogenen Daten, läuft lokal oder als statische Seite.

- Kern-Playbook gilt (Security-Regeln immer!).
- Git-Repo SOLL existieren; Commits direkt auf einem Branch sind ok, PR nicht nötig.
- Tests für zentrale Logik SOLLEN vorhanden sein.
- Kein Dockerfile nötig.

## Stufe 2 – Team

**Wann:** Mehrere Kolleginnen/Kollegen nutzen die App, oder sie verarbeitet interne Daten.

Zusätzlich zu Stufe 1:

- Repo MUSS auf der zentralen Git-Plattform liegen, `main` geschützt.
- Änderungen nur per Pull Request mit mindestens einem menschlichen Review.
- CI MUSS laufen: Format, Lint, Typen, Tests, Secret-Scan, Dependency-Scan (Vorlage: `security.md`).
- Agent legt vor nicht-trivialen Änderungen einen Plan vor und wartet auf Bestätigung.
- Hosting intern als Container hinter Reverse Proxy mit SSO (`hosting.md`).
- PostgreSQL statt SQLite, wenn mehrere Nutzer gleichzeitig schreiben.
- Owner und Vertretung sind eingetragen.

## Stufe 3 – produktiv

**Wann:** Geschäftsrelevant, personenbezogene oder vertrauliche Daten, oder Schnittstellen zu Kernsystemen (ERP, CRM, HR …).

Zusätzlich zu Stufe 2:

- Freigabe durch IT/Security vor dem ersten Produktivbetrieb.
- Getrennte Umgebungen: Test und Produktion, mit getrennten Zugangsdaten.
- SAST (z. B. Semgrep) und Container-Scan (z. B. Trivy) in der CI; Funde mit Schweregrad hoch/kritisch blockieren den Merge.
- Testabdeckung für Fachlogik verbindlich; Schnittstellen über Verträge/Mocks getestet.
- Monitoring, Health-Checks, Alarmierung und Backups eingerichtet und getestet.
- Datenschutz geprüft (Verarbeitungsverzeichnis, Löschkonzept), wenn personenbezogene Daten verarbeitet werden.
- Betriebsdoku in `README.md`: Deployment, Rollback, Ansprechpartner.
- Der Agent ändert NIEMALS Produktiv-Konfiguration oder -Daten direkt.
- Nachweisführung nach `compliance.md`: Issue-Pflicht, Funktionstrennung (Autor ≠ Freigeber ≠ alleiniger Deployer), CODEOWNERS für sensible Bereiche, 2 Freigaben oder Code-Owner-Freigabe, geregelter Notfallprozess, Aufbewahrung von CI-Logs und Deployment-Historie.

## Compliance-Rahmen

Ist in `AGENTS.md` ein Compliance-Rahmen (ISO 27001, SOC 2, NIS2, intern) eingetragen, gelten die Regeln aus `compliance.md` mindestens wie Stufe 3, auch wenn die App sonst niedriger eingestuft wäre. Die konkreten Anforderungen legt das ISMS bzw. die Informationssicherheit des Unternehmens fest.
