# Auth Platform (Backend)

This folder contains the authentication service implemented in Python using FastAPI and managed with Poetry. It provides endpoints for registering and logging in users and includes tests and local development tooling.

Table of contents
- Overview
- Prerequisites
- Local development
- Running tests
- Linting
- Docker / Compose
- Notes on secrets

Overview
--------
The backend lives under this `auth_platform` directory. The FastAPI app entry point is `auth_platform/auth_platform/auth_service/main.py`.

Prerequisites
-------------
- Python 3.10+ (used in CI)
- Poetry for dependency management
- Node/npm only needed for the UI (not required here)

Setup
-----
1. Install dependencies with Poetry:

```bash
cd auth_platform
poetry install
```

2. Create a local environment variable file (do NOT commit it):

```bash
# Example .env (do not commit)
# SECRET_KEY=some-long-random-secret
# DATABASE_URL=sqlite:///./app.db
```

Run the app locally
-------------------
Start the FastAPI server with uvicorn (from inside the `auth_platform` directory):

```bash
cd auth_platform
poetry run uvicorn auth_platform.auth_service.main:app --reload --host 0.0.0.0 --port 8000
```

API Docs are available at `http://localhost:8000/docs` when running locally.

Running tests
-------------
Run backend tests with pytest via Poetry:

```bash
cd auth_platform
poetry run pytest -q
```

Linting
-------
Pylint is configured at the repository root and can be run via Poetry (or directly):

```bash
cd auth_platform
poetry run pylint auth_platform
```

CI
--
The repository includes a GitHub Actions workflow that runs detect-secrets, backend tests (Poetry/pytest), and UI unit tests. If CI fails on detect-secrets, update the `.secrets.baseline` after reviewing the candidates.

Docker
------
There is a Dockerfile under `auth_platform/` used by the top-level docker-compose. To build and run the service with Docker Compose from the repo root:

```bash
docker compose up --build auth_platform
```

Secrets and safety
------------------
- Never commit `.env` files or private keys. Add them to `.gitignore`.
- If you accidentally commit secrets, remove them from history and rotate the credentials (see project root README for guidance).

Where to find things
--------------------
- FastAPI app: `auth_platform/auth_platform/auth_service/main.py`
- Models: `auth_platform/auth_platform/auth_service/models.py`
- Auth helpers (hashing, tokens): `auth_platform/auth_platform/auth_service/auth.py`
- DB helpers: `auth_platform/auth_platform/auth_service/db.py`
- Tests: `auth_platform/auth_platform_tests`

Contact / Support
-----------------
Open an issue or create a pull request in the repo if something in the backend needs changes or additional documentation.
