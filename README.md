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