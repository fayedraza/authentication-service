# BAML Fraud Detection Agent

This directory contains the BAML schema for AI-powered fraud detection.

## Overview

The fraud detection agent analyzes authentication events and provides risk assessments using AI. It considers multiple factors including:

- Failed login and 2FA attempts
- IP address and user agent changes
- Timing patterns and event sequences
- Historical user behavior

## Setup

### Prerequisites

1. Install BAML CLI:
   ```bash
   npm install -g @boundaryml/baml
   ```

2. Configure your AI provider (OpenAI, Anthropic, etc.) in your environment:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

### Generate BAML Client

Run the BAML code generator to create the Python client:

```bash
cd mcp_server
baml-cli generate
```

This will generate a `baml_client` package with the `b` client object that can be imported.

### Enable BAML in MCP Server

Set the following environment variables:

```bash
BAML_ENABLED=true
BAML_TIMEOUT_MS=5000
```

## Schema

The BAML schema defines:

- **LoginEvent**: Input structure with authentication event details and context
- **FraudAssessment**: Output structure with risk score, alert flag, reason, and confidence
- **FraudCheck**: Function that performs the fraud analysis

## Usage

When BAML is enabled and the client is available, the FraudDetector will automatically use it for analysis. If BAML is unavailable or times out, it falls back to rule-based detection.

## Testing

To test the BAML integration:

1. Ensure BAML client is generated
2. Set `BAML_ENABLED=true` in your `.env` file
3. Ingest test events via the `/mcp/ingest` endpoint
4. Check the fraud analysis results in the database

## Fallback Behavior

The system is designed to be resilient:

- If BAML is disabled: Uses rule-based detection
- If BAML client is not available: Falls back to rule-based detection
- If BAML times out: Falls back to rule-based detection
- If BAML returns an error: Falls back to rule-based detection

This ensures the fraud detection system always provides results, even if the AI component is unavailable.
