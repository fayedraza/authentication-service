# MCP Server - Monitoring + Control Plane

## Overview

The MCP (Monitoring + Control Plane) Server is a standalone FastAPI service that consumes authentication events from the Auth Service, performs fraud detection analysis using rule-based and AI-powered methods, and provides alerting capabilities for high-risk authentication activity.

## Features

- **Event Ingestion**: Receive and store authentication events from Auth Service
- **Fraud Detection**: Analyze events using rule-based and BAML AI-powered detection
- **Risk Scoring**: Calculate risk scores (0-1) for each authentication event
- **Alert Generation**: Automatically generate alerts for high-risk events (score > 0.7)
- **Alert Consolidation**: Combine multiple high-risk events for the same user within 5 minutes
- **Query APIs**: Retrieve events, fraud assessments, and alerts with filtering and pagination
- **Health Checks**: Monitor service health and readiness

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Auth Service      │         │    MCP Server       │
│                     │  HTTP   │                     │
│  - Authentication   │────────>│  - Event Ingestion  │
│  - Event Logging    │  POST   │  - Fraud Detection  │
│  - User Management  │         │  - Risk Scoring     │
│                     │         │  - Alert Generation │
└─────────────────────┘         └─────────────────────┘
         │                               │
         v                               v
┌─────────────────────┐         ┌─────────────────────┐
│   Auth Database     │         │    MCP Database     │
└─────────────────────┘         └─────────────────────┘
                                         │
                                         v
                                ┌─────────────────────┐
                                │   BAML Agent        │
                                │  (Fraud Detection)  │
                                └─────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)

### Local Development Setup

1. **Clone the repository and navigate to the MCP server directory**:
   ```bash
   cd mcp_server
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**:
   ```bash
   # Database is automatically initialized on first startup
   ```

6. **Run the server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

7. **Access the API documentation**:
   - Swagger UI: http://localhost:8001/docs
   - ReDoc: http://localhost:8001/redoc

8. **Import Insomnia Collection** (optional):
   - Open Insomnia
   - Import `insomnia-collection.json`
   - Start testing with pre-configured requests

### Docker Deployment

1. **Build and run with Docker Compose** (from project root):
   ```bash
   docker-compose up -d mcp-server
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f mcp-server
   ```

3. **Stop the service**:
   ```bash
   docker-compose down
   ```

## Configuration

All configuration is managed through environment variables. Copy `.env.template` to `.env` and customize as needed.

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | `8001` | Port for the MCP server to listen on |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./mcp.db` | Database connection string (SQLite or PostgreSQL) |
| `DB_POOL_SIZE` | `5` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Maximum overflow connections |
| `EVENT_RETENTION_DAYS` | `90` | Number of days to retain events |

### Auth Service Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_SERVICE_URL` | `http://auth-service:8000` | URL of the Auth Service |

### Fraud Detection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FRAUD_THRESHOLD` | `0.7` | Risk score threshold for alert generation (0-1) |
| `RULE_BASED_FALLBACK` | `true` | Enable rule-based detection as fallback |
| `BAML_ENABLED` | `false` | Enable BAML AI-powered fraud detection |
| `BAML_TIMEOUT_MS` | `5000` | Timeout for BAML agent calls in milliseconds |

### Alert Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_CONSOLIDATION_WINDOW_MINUTES` | `5` | Time window for consolidating alerts (minutes) |
| `MAX_EVENTS_PER_ALERT` | `10` | Maximum events to consolidate into a single alert |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins |

## API Endpoints

### Event Ingestion

#### POST /mcp/ingest

Receive authentication events from Auth Service.

**Request Body**:
```json
{
  "user_id": 123,
  "username": "john.doe",
  "event_type": "login_success",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "session_id": "abc123",
    "device": "desktop"
  }
}
```

**Valid Event Types**:
- `login_success`
- `login_failure`
- `2fa_success`
- `2fa_failure`
- `password_reset`
- `password_reset_request`
- `account_locked`
- `account_unlocked`

**Response** (201 Created):
```json
{
  "message": "Event accepted for processing",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted"
}
```

**Error Response** (422 Unprocessable Entity):
```json
{
  "detail": "Invalid event structure",
  "error_type": "validation_error"
}
```

### Event Query

#### GET /mcp/events

Retrieve stored authentication events with filtering and pagination.

**Query Parameters**:
- `user_id` (optional): Filter by user ID
- `event_type` (optional): Filter by event type
- `start_date` (optional): ISO 8601 timestamp (e.g., `2024-01-01T00:00:00Z`)
- `end_date` (optional): ISO 8601 timestamp
- `limit` (optional, default=100): Maximum results per page
- `offset` (optional, default=0): Pagination offset

**Example Request**:
```bash
curl "http://localhost:8001/mcp/events?user_id=123&event_type=login_failure&limit=50"
```

**Response** (200 OK):
```json
{
  "events": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": 123,
      "username": "john.doe",
      "event_type": "login_failure",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0",
      "timestamp": "2024-01-15T10:30:00Z",
      "metadata": {},
      "risk_score": 0.8,
      "fraud_reason": "Multiple failed login attempts detected",
      "analyzed_at": "2024-01-15T10:30:01Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

### Fraud Assessments

#### GET /mcp/fraud-assessments

Query fraud detection results with statistics.

**Query Parameters**:
- `user_id` (optional): Filter by user ID
- `min_risk_score` (optional): Minimum risk score (0-1)
- `max_risk_score` (optional): Maximum risk score (0-1)
- `start_date` (optional): ISO 8601 timestamp
- `end_date` (optional): ISO 8601 timestamp
- `sort_by` (optional, default=risk_score): Sort field
- `order` (optional, default=desc): Sort order (asc/desc)
- `limit` (optional, default=100): Maximum results per page
- `offset` (optional, default=0): Pagination offset

**Example Request**:
```bash
curl "http://localhost:8001/mcp/fraud-assessments?min_risk_score=0.7&limit=20"
```

**Response** (200 OK):
```json
{
  "assessments": [
    {
      "event": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": 123,
        "username": "john.doe",
        "event_type": "login_failure",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "timestamp": "2024-01-15T10:30:00Z",
        "metadata": {},
        "risk_score": 0.8,
        "fraud_reason": "Multiple failed login attempts",
        "analyzed_at": "2024-01-15T10:30:01Z"
      },
      "risk_score": 0.8,
      "alert_generated": true,
      "reason": "Multiple failed login attempts",
      "analyzed_at": "2024-01-15T10:30:01Z"
    }
  ],
  "statistics": {
    "total_events": 1000,
    "high_risk_events": 15,
    "medium_risk_events": 85,
    "low_risk_events": 900,
    "average_risk_score": 0.18
  },
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### Alerts

#### GET /mcp/alerts

Retrieve security alerts with filtering.

**Query Parameters**:
- `status` (optional): Filter by status (open, reviewed, resolved)
- `min_risk_score` (optional): Minimum risk score (0-1)
- `user_id` (optional): Filter by user ID
- `limit` (optional, default=100): Maximum results per page
- `offset` (optional, default=0): Pagination offset

**Example Request**:
```bash
curl "http://localhost:8001/mcp/alerts?status=open&min_risk_score=0.7"
```

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "id": "alert-550e8400-e29b-41d4-a716-446655440000",
      "user_id": 123,
      "username": "john.doe",
      "event_ids": [
        "550e8400-e29b-41d4-a716-446655440000",
        "660e8400-e29b-41d4-a716-446655440001"
      ],
      "risk_score": 0.85,
      "reason": "Multiple failed login attempts from different IP addresses",
      "status": "open",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 25,
  "limit": 100,
  "offset": 0
}
```

#### PATCH /mcp/alerts/{alert_id}

Update alert status.

**Request Body**:
```json
{
  "status": "reviewed"
}
```

**Valid Status Values**:
- `open`
- `reviewed`
- `resolved`

**Response** (200 OK):
```json
{
  "id": "alert-550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "username": "john.doe",
  "event_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "risk_score": 0.85,
  "reason": "Multiple failed login attempts",
  "status": "reviewed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Health Checks

#### GET /health

Basic health check endpoint.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /ready

Readiness check with dependency status.

**Response** (200 OK):
```json
{
  "status": "ready",
  "database": "connected",
  "baml_agent": "available",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response** (503 Service Unavailable) - when not ready:
```json
{
  "status": "not_ready",
  "database": "disconnected",
  "baml_agent": "unavailable",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Fraud Detection

The MCP Server uses a two-tier fraud detection system:

### Rule-Based Detection (Default)

The rule-based engine analyzes authentication events using predefined patterns:

| Rule | Risk Score Increase | Description |
|------|---------------------|-------------|
| Multiple failed logins | +0.3 to +0.7 | 3-5 attempts: +0.3, 6-10: +0.5, 11+: +0.7 |
| Multiple failed 2FA | +0.4 to +0.8 | 3-5 attempts: +0.4, 6-10: +0.6, 11+: +0.8 |
| IP address change | +0.2 | Different IP from previous login |
| User agent change | +0.1 | Different user agent from previous login |
| Geographic anomaly | +0.3 | Login from new geographic location |
| Password reset + login | +0.2 | Password reset followed by immediate login |

**Risk Score Thresholds**:
- **High Risk** (> 0.7): Alert generated automatically
- **Medium Risk** (0.4 - 0.7): Logged for review
- **Low Risk** (< 0.4): Normal activity

### BAML AI-Powered Detection (Optional)

When enabled (`BAML_ENABLED=true`), the system uses a BAML agent for more sophisticated analysis:

- Analyzes patterns across multiple dimensions
- Considers historical user behavior
- Detects anomalous sequences
- Provides natural language reasoning
- Falls back to rule-based detection if unavailable

**Configuration**:
```bash
BAML_ENABLED=true
BAML_TIMEOUT_MS=5000
```

See [BAML Integration](#baml-integration) section for setup instructions.

## BAML Integration

BAML (Boundary ML) is a framework for defining AI agent schemas and prompts. The MCP Server can optionally use BAML for AI-powered fraud detection.

### Prerequisites

1. **AmpCode Account**: Sign up at [ampcode.ai](https://ampcode.ai)
2. **BAML CLI**: Install the BAML command-line tool
3. **API Key**: Obtain your BAML API key from AmpCode

### Setup Steps

1. **Install BAML CLI**:
   ```bash
   pip install baml-py
   ```

2. **Configure BAML Agent**:

   The fraud detection agent is defined in `agents/fraud_check.baml`:
   ```baml
   input LoginEvent {
     user_id: int
     username: string
     ip_address: string
     user_agent: string
     timestamp: string
     event_type: string
     failed_attempts_5min: int
     ip_changed: bool
     user_agent_changed: bool
   }

   output FraudAssessment {
     risk_score: float  // 0.0 to 1.0
     alert: bool
     reason: string
     confidence: float
   }

   prompt FraudCheck(LoginEvent):
     """
     Analyze this authentication event for signs of fraudulent activity.

     Consider:
     - Failed login/2FA attempts in recent history
     - Changes in IP address or user agent
     - Unusual timing patterns
     - Sequence of events (e.g., password reset followed by login)

     Return a risk score from 0 (no risk) to 1 (high risk), whether to alert,
     and a clear explanation of your reasoning.
     """
   ```

3. **Deploy to AmpCode**:
   ```bash
   cd agents
   baml deploy fraud_check.baml
   ```

4. **Configure Environment Variables**:
   ```bash
   BAML_ENABLED=true
   BAML_API_KEY=your_api_key_here
   BAML_TIMEOUT_MS=5000
   ```

5. **Test BAML Integration**:
   ```bash
   python -m pytest tests/test_fraud_detector.py -k baml
   ```

### Fallback Behavior

If BAML is unavailable or times out:
- The system automatically falls back to rule-based detection
- A warning is logged but event processing continues
- No impact on event ingestion or storage

## Manual Testing Guide

### Quick Start Testing

**Best Practice**: Open two terminal windows:
1. **Terminal 1**: `docker compose logs -f mcp-server` (watch logs live)
2. **Terminal 2**: Run tests with Insomnia or curl

**Insomnia Collections**:
- `email-notification-insomnia.json` - Email notification testing (recommended)
- `insomnia-collection.json` - Full MCP Server API
- `../complete-insomnia-collection.json` - Complete Auth + MCP flow

---

### 🔴 Live Log Monitoring (Recommended for Testing)

For the best testing experience, monitor logs in real-time to see email notification triggers:

**Terminal 1 - Start Live Logs**:
```bash
cd auth_platform
docker compose logs -f mcp-server
```

**Terminal 2 - Run Your Tests** (Insomnia, curl, or test scripts)

**What You'll See in Logs**:
```
INFO: Event ingested successfully: id=abc123, user_id=456, event_type=login_failure
INFO: Rule-based fraud analysis complete for user 456: risk_score=0.80, email_notification=True
WARNING: ⚠️ HIGH RISK EVENT DETECTED: event_id=abc123, user_id=456, username=test.user@example.com, risk_score=0.80, reason=Multiple failed login attempts detected
WARNING: 📧 EMAIL NOTIFICATION TRIGGER: Would send email to user test.user@example.com about suspicious activity. Risk: 0.80 - Multiple failed login attempts detected
```

**Filter for Email Notifications Only**:
```bash
docker compose logs -f mcp-server | grep -E "(HIGH RISK|EMAIL)"
```

**Stop Live Logs**: Press `Ctrl+C`

---

### Test Event Ingestion

1. **Start the MCP Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001
   ```

2. **Send a test event**:
   ```bash
   curl -X POST http://localhost:8001/mcp/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 123,
       "username": "test.user",
       "event_type": "login_success",
       "ip_address": "192.168.1.100",
       "user_agent": "Mozilla/5.0",
       "timestamp": "2024-01-15T10:30:00Z",
       "metadata": {}
     }'
   ```

3. **Verify event was stored**:
   ```bash
   curl http://localhost:8001/mcp/events?user_id=123
   ```

### Test Email Notification Triggers

**Using Insomnia** (Easiest):

1. **Import Collection**: `email-notification-insomnia.json`
2. **Start Live Logs**: `docker compose logs -f mcp-server | grep EMAIL`
3. **Run Test Scenario**:
   - Folder: "1. Trigger Email Notifications"
   - Run: "Brute Force - Attempt 1, 2, 3"
4. **Watch Logs**: You'll see `📧 EMAIL NOTIFICATION TRIGGER` message
5. **Verify in API**:
   - Folder: "2. Verify Email Notifications"
   - Run: "Check Fraud Assessments"
   - Look for: `"email_notification": true`

**Expected Log Output**:
```
WARNING: 📧 EMAIL NOTIFICATION TRIGGER: Would send email to user test.user@example.com
about suspicious activity. Risk: 0.80 - Multiple failed login attempts detected
```

---

### Test Fraud Detection

1. **Simulate multiple failed login attempts**:
   ```bash
   # Send 3 failed login events within 5 minutes
   for i in {1..3}; do
     curl -X POST http://localhost:8001/mcp/ingest \
       -H "Content-Type: application/json" \
       -d "{
         \"user_id\": 456,
         \"username\": \"suspicious.user\",
         \"event_type\": \"login_failure\",
         \"ip_address\": \"10.0.0.$i\",
         \"user_agent\": \"Mozilla/5.0\",
         \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
         \"metadata\": {}
       }"
     sleep 2
   done
   ```

2. **Check fraud assessments**:
   ```bash
   curl "http://localhost:8001/mcp/fraud-assessments?user_id=456&min_risk_score=0.5"
   ```

3. **Verify alert was generated**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?user_id=456&status=open"
   ```

### Test Alert Management

1. **Get alert ID from previous test**:
   ```bash
   ALERT_ID=$(curl -s "http://localhost:8001/mcp/alerts?user_id=456" | jq -r '.alerts[0].id')
   ```

2. **Update alert status**:
   ```bash
   curl -X PATCH "http://localhost:8001/mcp/alerts/$ALERT_ID" \
     -H "Content-Type: application/json" \
     -d '{"status": "reviewed"}'
   ```

3. **Verify status update**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?status=reviewed"
   ```

### Test IP Address Change Detection

1. **Send successful login from first IP**:
   ```bash
   curl -X POST http://localhost:8001/mcp/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 789,
       "username": "mobile.user",
       "event_type": "login_success",
       "ip_address": "192.168.1.100",
       "user_agent": "Mozilla/5.0",
       "timestamp": "2024-01-15T10:00:00Z",
       "metadata": {}
     }'
   ```

2. **Send login from different IP shortly after**:
   ```bash
   curl -X POST http://localhost:8001/mcp/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 789,
       "username": "mobile.user",
       "event_type": "login_success",
       "ip_address": "203.0.113.50",
       "user_agent": "Mozilla/5.0",
       "timestamp": "2024-01-15T10:05:00Z",
       "metadata": {}
     }'
   ```

3. **Check risk score for IP change**:
   ```bash
   curl "http://localhost:8001/mcp/fraud-assessments?user_id=789"
   ```

### Test Alert Consolidation

1. **Send multiple high-risk events within 5 minutes**:
   ```bash
   # Send 5 failed login attempts
   for i in {1..5}; do
     curl -X POST http://localhost:8001/mcp/ingest \
       -H "Content-Type: application/json" \
       -d "{
         \"user_id\": 999,
         \"username\": \"attack.target\",
         \"event_type\": \"login_failure\",
         \"ip_address\": \"10.0.0.$i\",
         \"user_agent\": \"curl/7.68.0\",
         \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
         \"metadata\": {}
       }"
     sleep 10
   done
   ```

2. **Verify only one consolidated alert was created**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?user_id=999" | jq '.total'
   # Should return 1, not 5
   ```

3. **Check that alert contains multiple event IDs**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?user_id=999" | jq '.alerts[0].event_ids'
   ```

### Test Health Endpoints

1. **Check basic health**:
   ```bash
   curl http://localhost:8001/health
   ```

2. **Check readiness with dependencies**:
   ```bash
   curl http://localhost:8001/ready
   ```

3. **Test with database disconnected** (stop database container):
   ```bash
   docker-compose stop mcp-server
   curl http://localhost:8001/ready
   # Should return 503 Service Unavailable
   ```

### Test Query Filtering and Pagination

1. **Query events by date range**:
   ```bash
   curl "http://localhost:8001/mcp/events?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z"
   ```

2. **Query with pagination**:
   ```bash
   # First page
   curl "http://localhost:8001/mcp/events?limit=10&offset=0"

   # Second page
   curl "http://localhost:8001/mcp/events?limit=10&offset=10"
   ```

3. **Query fraud assessments sorted by risk score**:
   ```bash
   curl "http://localhost:8001/mcp/fraud-assessments?sort_by=risk_score&order=desc&limit=20"
   ```

4. **Filter alerts by risk score**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?min_risk_score=0.8"
   ```

### Integration Test with Auth Service

1. **Start both services**:
   ```bash
   docker-compose up -d auth-service mcp-server
   ```

2. **Perform authentication in Auth Service**:
   ```bash
   # Register a user
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "integration.test",
       "email": "test@example.com",
       "password": "SecurePass123!"
     }'

   # Attempt login with wrong password (should trigger fraud detection)
   for i in {1..3}; do
     curl -X POST http://localhost:8000/auth/login \
       -H "Content-Type: application/json" \
       -d '{
         "username": "integration.test",
         "password": "WrongPassword"
       }'
   done
   ```

3. **Verify events were sent to MCP Server**:
   ```bash
   curl "http://localhost:8001/mcp/events?username=integration.test"
   ```

4. **Check if alert was generated**:
   ```bash
   curl "http://localhost:8001/mcp/alerts?username=integration.test"
   ```

## Running Tests

### Unit Tests

Run all unit tests:
```bash
pytest tests/test_fraud_detector.py -v
```

Run specific test:
```bash
pytest tests/test_fraud_detector.py::test_multiple_failed_logins -v
```

### Integration Tests

Run all integration tests:
```bash
pytest tests/test_integration.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=mcp_server --cov-report=html
```

### Manual Test Scripts

The repository includes several manual test scripts:

- `test_ingest_manual.py` - Test event ingestion
- `test_fraud_detection.py` - Test fraud detection rules
- `test_alerts.py` - Test alert generation and management
- `test_events_query.py` - Test event query API
- `test_fraud_assessments.py` - Test fraud assessment API
- `test_alert_verification.py` - Verify alert consolidation
- `test_requirements_verification.py` - Verify all requirements

Run a manual test:
```bash
python test_ingest_manual.py
```

## Database Management

### View Database Contents

Using SQLite CLI:
```bash
sqlite3 mcp.db

# List tables
.tables

# View events
SELECT * FROM mcp_auth_events LIMIT 10;

# View alerts
SELECT * FROM mcp_alerts WHERE status = 'open';

# Exit
.quit
```

### Reset Database

```bash
# Stop the server
docker-compose down

# Remove database file
rm mcp.db

# Restart server (database will be recreated)
docker-compose up -d mcp-server
```

### Backup Database

```bash
# Create backup
cp mcp.db mcp.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp mcp.db.backup.20240115_103000 mcp.db
```

## Troubleshooting

### Server Won't Start

**Problem**: Server fails to start with database error

**Solution**:
```bash
# Check if database file is corrupted
rm mcp.db
# Restart server to recreate database
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Events Not Being Received

**Problem**: Auth Service events not appearing in MCP Server

**Solution**:
1. Check Auth Service configuration:
   ```bash
   # Verify MCP_SERVER_URL is set correctly
   docker-compose exec auth-service env | grep MCP_SERVER_URL
   ```

2. Check network connectivity:
   ```bash
   docker-compose exec auth-service curl http://mcp-server:8001/health
   ```

3. Check MCP Server logs:
   ```bash
   docker-compose logs -f mcp-server
   ```

### Fraud Detection Not Working

**Problem**: Risk scores are always 0 or null

**Solution**:
1. Verify fraud detection is enabled:
   ```bash
   # Check configuration
   cat .env | grep FRAUD_THRESHOLD
   ```

2. Check for errors in fraud detector:
   ```bash
   docker-compose logs mcp-server | grep -i fraud
   ```

3. Test fraud detection manually:
   ```bash
   python test_fraud_detection.py
   ```

### BAML Agent Unavailable

**Problem**: BAML agent calls timing out or failing

**Solution**:
1. Verify BAML is enabled and configured:
   ```bash
   cat .env | grep BAML
   ```

2. Check BAML API key is valid:
   ```bash
   # Test BAML connection
   python -c "from baml_client import test_connection; test_connection()"
   ```

3. Increase timeout:
   ```bash
   # In .env
   BAML_TIMEOUT_MS=10000
   ```

4. Enable fallback to rule-based detection:
   ```bash
   # In .env
   RULE_BASED_FALLBACK=true
   ```

### High Memory Usage

**Problem**: MCP Server consuming too much memory

**Solution**:
1. Reduce database pool size:
   ```bash
   # In .env
   DB_POOL_SIZE=3
   DB_MAX_OVERFLOW=5
   ```

2. Implement event retention:
   ```bash
   # In .env
   EVENT_RETENTION_DAYS=30
   ```

3. Add cleanup job (cron):
   ```bash
   # Delete old events
   sqlite3 mcp.db "DELETE FROM mcp_auth_events WHERE timestamp < datetime('now', '-30 days');"
   ```

## Performance Considerations

### Event Ingestion Rate

The MCP Server is designed to handle high-volume event ingestion:

- **Target**: 100+ events/second
- **Async Processing**: Fraud detection runs asynchronously
- **Database Indexing**: Optimized indexes on user_id, timestamp, event_type

### Query Performance

For optimal query performance:

- Use specific filters (user_id, event_type) rather than broad queries
- Implement pagination for large result sets
- Consider adding database indexes for frequently queried fields
- Use date range filters to limit result sets

### Scaling Recommendations

For production deployments:

1. **Database**: Migrate from SQLite to PostgreSQL for better concurrency
2. **Caching**: Add Redis for frequently accessed data
3. **Load Balancing**: Deploy multiple MCP Server instances behind a load balancer
4. **Message Queue**: Replace HTTP push with Kafka/RabbitMQ for event streaming
5. **Monitoring**: Add Prometheus metrics and Grafana dashboards

## Security Considerations

### Authentication

Currently, the MCP Server does not require authentication. For production:

1. Add API key authentication:
   ```python
   from fastapi import Security, HTTPException
   from fastapi.security import APIKeyHeader

   api_key_header = APIKeyHeader(name="X-API-Key")

   async def verify_api_key(api_key: str = Security(api_key_header)):
       if api_key != settings.API_KEY:
           raise HTTPException(status_code=403, detail="Invalid API key")
   ```

2. Use mutual TLS for service-to-service communication

### Data Privacy

- Store minimal PII (Personally Identifiable Information)
- Consider hashing IP addresses if required by privacy policy
- Implement data retention policies
- Ensure compliance with GDPR, CCPA, and other regulations

### Network Security

- Use HTTPS in production (configure reverse proxy)
- Restrict CORS origins to known services
- Implement rate limiting to prevent DoS attacks
- Use firewall rules to limit access to trusted networks

## Project Structure

```
mcp_server/
├── agents/                 # BAML agent definitions
│   └── fraud_check.baml   # Fraud detection agent schema
├── routes/                # API route handlers
│   ├── ingest.py         # Event ingestion endpoint
│   ├── events.py         # Event query endpoint
│   ├── fraud_assessments.py  # Fraud assessment queries
│   ├── alerts.py         # Alert management
│   └── health.py         # Health check endpoints
├── tests/                # Test suite
│   ├── test_fraud_detector.py  # Unit tests
│   └── test_integration.py     # Integration tests
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── db.py                # Database connection and initialization
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── fraud_detector.py    # Fraud detection engine
├── baml_client.py       # BAML integration client
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
├── .env.template        # Environment variable template
└── README.md           # This file
```

## Contributing

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make changes and add tests:
   ```bash
   # Add your changes
   # Write tests in tests/
   ```

3. Run tests and linting:
   ```bash
   pytest tests/ -v
   pylint mcp_server/
   ```

4. Commit and push:
   ```bash
   git add .
   git commit -m "Add your feature description"
   git push origin feature/your-feature-name
   ```

5. Create a pull request

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

### Adding New Endpoints

1. Create route handler in `routes/` directory
2. Define request/response schemas in `schemas.py`
3. Add database models if needed in `models.py`
4. Write unit tests in `tests/`
5. Update this README with API documentation

## License

[Add your license information here]

## Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [Full Documentation](https://docs.your-domain.com)
- **Email**: support@your-domain.com

## Changelog

### Version 1.0.0 (2024-01-15)

- Initial release
- Event ingestion API
- Rule-based fraud detection
- BAML AI-powered fraud detection
- Alert generation and management
- Query APIs with filtering and pagination
- Health check endpoints
- Docker deployment support

## API Testing

### Insomnia Collection

An Insomnia API collection is included with 30+ pre-configured requests:

**Import Instructions:**
1. Open Insomnia
2. Click **Create** → **Import From** → **File**
3. Select `insomnia-collection.json`
4. Start testing!

**Collection Contents:**
- Health checks and service info
- Event ingestion examples (all event types)
- Event query with filters and pagination
- Fraud assessment queries with statistics
- Alert management (create, query, update)
- Test scenarios (brute force, IP changes)

See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for detailed testing guide.

## Related Documentation

- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - What we built and how to test it
- [Insomnia Collection](insomnia-collection.json) - API testing collection
- [BAML Integration Guide](BAML_INTEGRATION.md) - Detailed BAML setup and usage
- [Alert Implementation Summary](ALERT_IMPLEMENTATION_SUMMARY.md) - Alert system details
- [Auth Service Documentation](../auth_platform/README.md) - Auth Service integration
- [Design Document](.kiro/specs/mcp-server-integration/design.md) - System architecture
- [Requirements Document](.kiro/specs/mcp-server-integration/requirements.md) - Feature requirements
