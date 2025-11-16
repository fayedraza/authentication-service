# Authenication Service

This repository contains a small authentication service (FastAPI backend) and a React-based developer portal UI.

Layout
- `auth_platform/` — Python backend (Poetry-managed). Contains the FastAPI service, tests, and pyproject.
- `dev-portal-ui/dev-portal-ui/` — React frontend (npm). Contains UI source, tests, and package.json.

Getting started (local)

1. Backend (Poetry)

```bash
cd "auth_platform"
poetry install
poetry run uvicorn auth_platform.auth_service.main:app --reload --host 0.0.0.0 --port 8000
```

Run backend tests:

```bash
cd auth_platform
poetry run pytest -q
```

2. Frontend (UI)

```bash
cd dev-portal-ui/dev-portal-ui
npm ci
npm start
```

Run UI tests:

```bash
cd dev-portal-ui/dev-portal-ui
npm test -- --watchAll=false
```

## Two-Factor Authentication (TOTP)

Backend
- Endpoints:
	- POST `/login`: If the user has 2FA enabled, returns `{ "requires2fa": true }` (no token yet). Otherwise returns `{ "access_token": "..." }`.
	- POST `/2fa/enroll`: Enrolls the authenticated user for 2FA (in dev tier, protected via username/password in request). Returns an `otpauth://` URI for QR.
	- POST `/2fa/verify`: Validates a 6-digit TOTP code and returns `{ "access_token": "..." }`.
- Configuration:
	- `AUTH_SERVICE_ISSUER` (env): Issuer shown in the authenticator app (default `AuthService`).

Frontend
- Account page (`/account`): Click “Enable 2FA”, which calls `/2fa/enroll` and renders the returned `otpauth://` as a QR (via `qrcode.react`).
- Login flow: If `/login` responds with `requires2fa`, the UI prompts for the 6-digit code and submits it to `/2fa/verify` to complete login.

Security notes
- Do not expose raw TOTP secrets to the client; only return the `otpauth://` URI.
- Avoid logging TOTP secrets or codes. Use environment variables for issuer and other auth-related config and never commit `.env` files.

Pre-commit and secret scanning

- Install dev tooling (locally):

```bash
python -m pip install --user pre-commit detect-secrets
~/.local/bin/pre-commit install
```

- To create or update the detect-secrets baseline (review before committing):

```bash
~/.local/bin/detect-secrets scan --all-files > .secrets.baseline
# review .secrets.baseline before committing
git add .secrets.baseline && git commit -m "chore: update detect-secrets baseline"
```

Linting

- Pylint is configured in `.pre-commit-config.yaml` and will run on Python files via pre-commit. You can also run it manually:

```bash
poetry run pylint auth_platform/auth_platform
```

CI

- GitHub Actions workflow `.github/workflows/ci.yml` runs detect-secrets, backend tests (Poetry), and UI unit tests (npm).

Security note

- Never commit `.env` files, SSH keys, or other secrets. If you find credentials accidentally committed, follow the steps in the repo's CONTRIBUTING/SECURITY notes to remove them from history and rotate keys.
# Authentication Service Repository

This repository contains two services composed together for local development:

- `auth_platform` — FastAPI authentication service (JWT, user register/login)
- `dev_portal_ui` — Frontend (React) dev portal that calls the auth API

## Prerequisites

- Docker (Desktop) with Compose support (v2 recommended). If you have an older `docker-compose` binary, the commands below include alternatives.
- (Optional for running unit tests) Poetry and Python 3.12

## Run with Docker Compose (recommended)

From the repository root (this file's directory):

```bash
cd "/Users/fayedraza/Authenication Service"
# Using Docker Compose V2 (recommended)
docker compose up -d --build

# Or, if you have the standalone docker-compose binary:
# docker-compose up -d --build
```

This builds both the `auth_platform` and `dev_portal_ui` images and starts them in detached mode.

Services will be available at:

- Auth service OpenAPI: http://localhost:8000/openapi.json
- Auth service Swagger UI: http://localhost:8000/docs
- Frontend UI: http://localhost:3000/

To stop and remove the containers:

```bash
docker compose down
# or: docker-compose down
```

## Run a single service (auth) via Docker

Build the image and run the auth service alone:

```bash
cd "/Users/fayedraza/Authenication Service/auth_platform"
docker build -t auth_platform:local -f Dockerfile .
docker run -d --name auth_platform -p 8000:8000 auth_platform:local
```

Then visit http://localhost:8000/docs to verify the API is up.

## Run tests locally (Poetry)

If you want to run unit tests locally (not required for Docker):

```bash
cd "/Users/fayedraza/Authenication Service/auth_platform"
poetry install
poetry run pytest -q
```

## Notes & tips

- The project uses relative imports inside the `auth_platform` package so it works when installed by Poetry or run from the repo root.
- Dockerfile sets `PYTHONPATH=/app` so the container resolves the package the same as the local environment.
- You may see a few deprecation warnings from dependencies (FastAPI on_event, SQLAlchemy declarative_base, datetime usage). These do not affect functionality but can be cleaned up later.

If you want, I can add a `/health` endpoint, fix the deprecation warnings, or update this README with more developer notes. Let me know which you'd like next.
