# Hosting – Details

Ergänzt `AGENTS.md` Abschnitt 8. Gilt ab Stufe 2.

## Grundsätze

- Eine App = ein Container. Konfiguration nur über Umgebungsvariablen.
- Container läuft als Nicht-Root-Nutzer, enthält keine Secrets und keine Entwicklungswerkzeuge.
- Erreichbar nur im internen Netz/VPN, über einen Reverse Proxy mit HTTPS.
- Authentifizierung macht der Proxy (SSO, z. B. Entra ID per OIDC). Die App liest die Identität aus Headern, die der Proxy setzt (z. B. `X-Forwarded-Email`), und vertraut diesen nur, wenn sie ausschließlich über den Proxy erreichbar ist.
- Rein statische Apps (nur HTML/JS) brauchen keinen Container, sondern einen Webserver oder Static Hosting.

## Dockerfile (Vorlage für FastAPI mit uv)

```dockerfile
# --- Build-Stufe ---
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Erst nur Abhängigkeiten (besseres Layer-Caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Dann den Code
COPY src ./src
RUN uv sync --frozen --no-dev

# --- Laufzeit-Stufe ---
FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "<paket>.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

In Produktion das `uv`-Image auf eine feste Version pinnen statt `latest`.

## .dockerignore

```
.git
.venv
.env
__pycache__/
.mypy_cache/
.ruff_cache/
.pytest_cache/
tests/
*.sqlite
*.db
```

## Health-Endpoint

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for proxy and container runtime."""
    return {"status": "ok"}
```

## Referenz-Setup: interner Server mit Docker Compose

Aufbau: Traefik (Reverse Proxy, HTTPS) → oauth2-proxy (SSO) → App. Die App ist nicht direkt erreichbar.

```yaml
services:
  traefik:
    image: traefik:v3
    command:
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.websecure.address=:443
    ports:
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # interne TLS-Zertifikate der IT hier einbinden

  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:latest
    env_file: oauth2-proxy.env   # Client-ID/Secret, Issuer-URL – nicht im Repo!
    command:
      - --provider=oidc
      - --upstream=http://app:8000
      - --http-address=0.0.0.0:4180
      - --email-domain=<firma.de>
      - --pass-user-headers=true
      - --reverse-proxy=true
    labels:
      - traefik.enable=true
      - traefik.http.routers.app.rule=Host(`<app>.intern.<firma.de>`)
      - traefik.http.routers.app.entrypoints=websecure
      - traefik.http.routers.app.tls=true
      - traefik.http.services.app.loadbalancer.server.port=4180

  app:
    image: <registry>/<app>:<version>
    env_file: app.env            # aus Secret-Store befüllt, nicht im Repo
    restart: unless-stopped
    # keine "ports": nur über oauth2-proxy erreichbar
```

Dies ist ein Ausgangspunkt, kein fertiges Produktions-Setup. Zertifikate, DNS, Netzsegment und SSO-App-Registrierung kommen von der IT. Image-Versionen pinnen.

## Deployment-Ablauf

1. Merge in `main` → CI baut das Image, taggt es mit Version/Commit-SHA und pusht es in die Registry.
2. Deployment auf Testumgebung, Smoke-Test über `/health` und Kernfunktion.
3. Ab Stufe 3: Freigabe, dann Deployment Produktion mit demselben Image (nie neu bauen).
4. Rollback: vorheriges Image-Tag erneut deployen.

## Für den Agent

- Dockerfile und Compose nach dieser Vorlage erstellen, nicht frei erfinden.
- NIEMALS Secrets in Dockerfile, Compose-Datei oder Image einbauen.
- Keine Ports der App direkt nach außen öffnen.
- Deployments auf geteilte Server nur auf ausdrückliche Anweisung.
