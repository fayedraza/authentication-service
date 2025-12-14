# Multi-stage Dockerfile for MCP Server
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy pyproject.toml first for better caching
COPY pyproject.toml ./mcp_server/

# Development stage - includes test dependencies
FROM base as development

# Install the package with all dependencies (including test and dev dependencies)
RUN cd mcp_server && pip install --no-cache-dir -e .[test,dev]

# Copy the entire mcp_server directory
COPY . ./mcp_server/

# Set PYTHONPATH to ensure imports work correctly
ENV PYTHONPATH=/workspace

# Expose port 8001
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command to run the application
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Production stage - minimal dependencies
FROM base as production

# Install only production dependencies
RUN cd mcp_server && pip install --no-cache-dir -e .

# Copy the entire mcp_server directory
COPY . ./mcp_server/

# Set PYTHONPATH to ensure imports work correctly
ENV PYTHONPATH=/workspace

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port 8001
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command to run the application
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Test stage - for running tests in CI
FROM development as test

# Run tests by default
CMD ["python", "-m", "pytest", "mcp_server/tests/", "-v"]
