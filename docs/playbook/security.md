# Security – Details

Ergänzt `AGENTS.md` Abschnitt 5. Leitgedanke: Das Playbook sorgt dafür, dass Code sicher geschrieben wird; die CI sorgt dafür, dass Fehler trotzdem auffallen. Beides ist nötig.

## Secrets

- Konfiguration über `pydantic-settings`, Werte aus Umgebungsvariablen. Secrets als `SecretStr` typisieren, damit sie nicht versehentlich geloggt werden.
- `.env` steht in `.gitignore`; `.env.example` enthält jede Variable mit Platzhalter, nie mit echtem Wert.
- In Produktion kommen Secrets aus einem Secret-Store (z. B. Vault, Azure Key Vault), nicht aus Dateien im Repo.
- Wird ein Secret im Code oder in der Git-Historie gefunden: sofort melden, Secret beim Anbieter rotieren, erst danach Historie bereinigen.

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: SecretStr
    api_token: SecretStr
    log_level: str = "INFO"
```

## Abhängigkeiten

- Vor dem Hinzufügen prüfen: Existiert das Paket wirklich auf PyPI unter genau diesem Namen? Wird es gepflegt (letztes Release, Maintainer, Downloads)?
- KI-Tools schlagen manchmal nicht existierende Paketnamen vor. Angreifer registrieren solche Namen gezielt. Niemals ein Paket installieren, das nur „plausibel klingt“.
- Versionen über `uv.lock` fixieren; Updates per Dependabot/Renovate-PR.

## Eingaben & Ausgaben

- Jede Eingabe von außen (HTTP, Dateien, CLI, Umgebung, Fremdsysteme) über ein Pydantic-Modell validieren: Typ, Länge, Wertebereich.
- Datei-Uploads: Größe begrenzen, Dateityp prüfen, Dateinamen nie direkt als Pfad verwenden (Path Traversal).
- HTML-Ausgabe nur über Template-Engine mit Auto-Escaping (Jinja2 mit `autoescape=True`).
- Externe HTTP-Aufrufe immer mit Timeout; Zertifikatsprüfung nie abschalten (`verify=False` ist verboten).

## Typische Schwachstellen in KI-generiertem Code

| Muster | Stattdessen |
|---|---|
| f-String in SQL | ORM oder gebundene Parameter |
| `subprocess.run(cmd, shell=True)` | Liste von Argumenten, `shell=False` |
| `yaml.load(...)` | `yaml.safe_load(...)` |
| `pickle.loads(fremd)` | JSON + Pydantic |
| `verify=False` | Korrekte CA konfigurieren |
| Hartkodiertes Passwort „nur zum Testen“ | Umgebungsvariable, Testwert in Fixture |
| `except Exception: pass` | Spezifische Exception, loggen, sauber reagieren |
| CORS `allow_origins=["*"]` | Konkrete erlaubte Origins |

## Automatische Prüfungen (CI)

| Prüfung | Werkzeug (Beispiel) | Ab Stufe |
|---|---|---|
| Secret-Scan | Gitleaks | 1 (lokal empfohlen), 2 Pflicht |
| Dependency-Scan | `pip-audit`, Dependabot | 2 |
| Security-Linting | `ruff` mit Regelset `S` (Bandit-Regeln) | 1 |
| SAST | Semgrep oder CodeQL | 3 |
| Container-Scan | Trivy | 3 |

Ruff-Konfiguration (Ausschnitt `pyproject.toml`):

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S", "SIM"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert ist in Tests erlaubt
```

Beispiel-Workflow (GitHub Actions, `.github/workflows/ci.yml`):

```yaml
name: ci
on: [pull_request]

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - run: uv run ruff format --check .
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest
      - run: uvx pip-audit
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Versionen der Actions vor Verwendung prüfen und auf aktuelle Releases (oder Commit-SHAs) setzen. Die Gitleaks-Action braucht in GitHub-Organisationen eine Lizenz; alternativ das Gitleaks-CLI direkt aufrufen oder das eingebaute Secret Scanning der Plattform nutzen.

## Daten & KI-Tools

- Keine Firmendaten, Kundendaten oder personenbezogenen Daten in Prompts, wenn das Tool dafür nicht freigegeben ist.
- Testdaten synthetisch erzeugen (z. B. mit `faker`), nie aus Produktivsystemen kopieren.
