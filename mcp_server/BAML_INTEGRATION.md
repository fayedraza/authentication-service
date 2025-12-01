# BAML Integration for Fraud Detection

This document describes the BAML (Boundary ML) integration for AI-powered fraud detection in the MCP Server.

## Overview

The MCP Server supports two fraud detection methods:

1. **Rule-Based Detection** (Default): Uses predefined scoring rules
2. **BAML AI Agent** (Optional): Uses AI for sophisticated pattern analysis

The system automatically falls back to rule-based detection if BAML is unavailable or encounters errors.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FraudDetector                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  analyze_event()                                     │  │
│  │    ├─> BAML enabled? ──Yes──> _baml_analysis()      │  │
│  │    │                              │                  │  │
│  │    │                              ├─> Success ──┐    │  │
│  │    │                              │             │    │  │
│  │    │                              └─> Fail ─────┤    │  │
│  │    │                                            │    │  │
│  │    └─> No ─────────────────────────────────────┤    │  │
│  │                                                 │    │  │
│  │                                                 ▼    │  │
│  │                                    _rule_based_analysis() │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. BAML Schema (`agents/fraud_check.baml`)

Defines the AI agent interface:

- **LoginEvent**: Input with authentication details and context
- **FraudAssessment**: Output with risk score, alert flag, reason, and confidence
- **FraudCheck**: Function that performs the analysis

### 2. BAML Client (`baml_client.py`)

Provides a Python interface to the BAML agent:

- **BAMLClient**: Manages connection to BAML runtime
- **LoginEvent**: Input data structure
- **BAMLFraudAssessment**: Output data structure
- **get_baml_client()**: Singleton factory function

### 3. FraudDetector Integration (`fraud_detector.py`)

Enhanced FraudDetector with BAML support:

- **`__init__`**: Accepts `baml_enabled` and `baml_timeout_ms` parameters
- **`analyze_event`**: Routes to BAML or rule-based analysis
- **`_baml_analysis`**: Gathers context and calls BAML agent
- **`_rule_based_analysis`**: Fallback detection method

## Configuration

### Environment Variables

```bash
# Enable BAML fraud detection
BAML_ENABLED=true

# Timeout for BAML agent calls (milliseconds)
BAML_TIMEOUT_MS=5000

# AI Provider API Key (depends on provider)
OPENAI_API_KEY=your-api-key-here
# or
ANTHROPIC_API_KEY=your-api-key-here
```

### Configuration in Code

```python
from mcp_server.fraud_detector import FraudDetector
from mcp_server.config import settings

detector = FraudDetector(
    fraud_threshold=settings.FRAUD_THRESHOLD,
    baml_enabled=settings.BAML_ENABLED,
    baml_timeout_ms=settings.BAML_TIMEOUT_MS
)
```

## Setup Instructions

### 1. Install BAML CLI

```bash
npm install -g @boundaryml/baml
```

### 2. Generate BAML Client

From the `mcp_server` directory:

```bash
baml-cli generate
```

This creates a `baml_client` package with the generated Python client.

### 3. Configure AI Provider

Set your AI provider API key:

```bash
# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Enable BAML in MCP Server

Update `.env`:

```bash
BAML_ENABLED=true
BAML_TIMEOUT_MS=5000
```

### 5. Restart MCP Server

```bash
# If running via Docker Compose
docker-compose restart mcp-server

# If running directly
uvicorn mcp_server.main:app --reload --port 8001
```

## Usage

Once configured, BAML is used automatically for all fraud detection:

```python
# Ingest an event (BAML analysis happens automatically)
POST /mcp/ingest
{
  "user_id": 123,
  "username": "john.doe",
  "event_type": "login_failure",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {}
}

# Response includes fraud analysis results
{
  "message": "Event accepted for processing",
  "event_id": "uuid-here",
  "status": "accepted"
}

# Query the event to see fraud analysis
GET /mcp/events?event_id=uuid-here
```

## Fallback Behavior

The system is designed to be resilient:

| Scenario | Behavior |
|----------|----------|
| BAML disabled | Uses rule-based detection |
| BAML client not generated | Falls back to rule-based detection |
| BAML timeout | Falls back to rule-based detection |
| BAML error | Falls back to rule-based detection |
| AI provider unavailable | Falls back to rule-based detection |

## Monitoring

Check logs to see which detection method is being used:

```
# BAML analysis successful
INFO: BAML fraud analysis complete for user 123: risk_score=0.85, confidence=0.92

# BAML fallback
WARNING: BAML analysis failed for user 123, falling back to rule-based detection
INFO: Rule-based fraud analysis complete for user 123: risk_score=0.80
```

## Testing

### Test BAML Availability

```python
from mcp_server.baml_client import get_baml_client

client = get_baml_client()
print(f"BAML available: {client.is_available()}")
```

### Test Fraud Detection

```bash
# Send a test event
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 999,
    "username": "test.user",
    "event_type": "login_failure",
    "ip_address": "10.0.0.1",
    "user_agent": "TestAgent/1.0",
    "timestamp": "2024-01-15T10:30:00Z",
    "metadata": {}
  }'

# Check the fraud analysis results
curl http://localhost:8001/mcp/fraud-assessments?user_id=999
```

## Performance Considerations

- **BAML Timeout**: Set appropriately based on your AI provider's latency
- **Fallback**: Rule-based detection is fast (<10ms), BAML may take 1-5 seconds
- **Caching**: Consider caching BAML results for similar patterns (future enhancement)
- **Rate Limiting**: AI providers may have rate limits, monitor usage

## Troubleshooting

### BAML Client Not Available

**Symptom**: Logs show "BAML client not available"

**Solution**:
1. Verify BAML CLI is installed: `baml-cli --version`
2. Generate client: `cd mcp_server && baml-cli generate`
3. Check for `baml_client` directory in `mcp_server/`

### BAML Timeout

**Symptom**: Logs show "BAML fraud analysis timed out"

**Solution**:
1. Increase timeout: `BAML_TIMEOUT_MS=10000`
2. Check AI provider status
3. Verify network connectivity

### AI Provider Errors

**Symptom**: BAML returns errors about API keys or quotas

**Solution**:
1. Verify API key is set correctly
2. Check API key has sufficient credits/quota
3. Review AI provider's status page

## Future Enhancements

- [ ] Support multiple AI providers with automatic failover
- [ ] Cache BAML results for similar event patterns
- [ ] A/B testing between BAML and rule-based detection
- [ ] Fine-tune BAML prompt based on feedback
- [ ] Train custom models on historical fraud data
- [ ] Real-time model performance monitoring

## References

- [BAML Documentation](https://docs.boundaryml.com/)
- [MCP Server Design Document](./design.md)
- [Fraud Detection Requirements](../.kiro/specs/mcp-server-integration/requirements.md)
