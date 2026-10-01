## Issue

<!-- Ab Stufe 2 Pflicht: Closes #<nr> / Refs #<nr> -->

## Was ändert sich?

<!-- 1–3 Sätze: Was macht dieser PR und warum? -->

## Risiko

- [ ] niedrig – kein Einfluss auf Daten, Zugriff oder Schnittstellen
- [ ] mittel – Fachlogik, Datenmodell oder Konfiguration betroffen
- [ ] hoch – Auth, personenbezogene Daten, Schnittstellen zu Kernsystemen, Infrastruktur

<!-- Bei "hoch": Rollback-Plan hier beschreiben -->

## Wie wurde getestet?

<!-- Welche Tests laufen, was wurde manuell geprüft? Nur angeben, was wirklich ausgeführt wurde. -->

- [ ] `uv run ruff format --check . && uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`

## Checkliste

- [ ] Nur der Auftrag umgesetzt, keine ungefragten Zusatzänderungen
- [ ] Neue Logik hat Tests
- [ ] Keine Secrets, keine echten personenbezogenen Daten
- [ ] `.env.example` und `README.md` aktuell
- [ ] Neue Abhängigkeiten begründet (unten)

## Neue Abhängigkeiten

<!-- Paket, Zweck, warum keine Alternative aus der Standardbibliothek. Sonst: "keine" -->

## Risiken & offene Punkte

<!-- Was sollte der Reviewer besonders ansehen? Was ist bewusst noch nicht gelöst? -->

## KI-Beteiligung

<!-- Welches Tool wurde genutzt, welche Teile sind KI-generiert? Verantwortlich für den Code ist die Person, die den PR stellt. -->

## Notfall-Änderung?

- [ ] Nein
- [ ] Ja – Begründung: … · nachträgliches Review bis: …
