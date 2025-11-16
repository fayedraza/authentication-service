# Use slim Python 3.12 image
FROM python:3.12-slim

# Set env vars
ENV POETRY_VERSION=1.8.2 \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:$PATH"

# Install Poetry
RUN apt-get update && apt-get install -y curl build-essential \
  && curl -sSL https://install.python-poetry.org | python3 - \
  && apt-get clean

ENV PYTHONPATH="${PYTHONPATH}:/app"

WORKDIR /app


# Set working dir
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# Copy only necessary files first (for better caching)
COPY . .

# Debug check
RUN poetry show uvicorn

# Run the app
CMD ["poetry", "run", "uvicorn", "auth_platform.auth_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
