# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy pyproject.toml first for better caching
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Expose port 8001
EXPOSE 8001

# Run the application
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
