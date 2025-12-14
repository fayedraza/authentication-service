# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory to parent directory
WORKDIR /workspace

# Copy the entire mcp_server directory
COPY . ./mcp_server/

# Install dependencies
RUN pip install --no-cache-dir fastapi==0.104.1 uvicorn==0.24.0 httpx==0.25.1 sqlalchemy==2.0.23 pydantic==2.8.2 pydantic-settings==2.4.0 python-dotenv==1.0.0

# Expose port 8001
EXPOSE 8001

# Set PYTHONPATH and run the application
ENV PYTHONPATH=/workspace
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
