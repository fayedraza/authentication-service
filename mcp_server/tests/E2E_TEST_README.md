# End-to-End Email Notification Test

This test suite verifies the complete authentication and fraud detection pipeline using testcontainers.

## Overview

The E2E test simulates a real-world scenario:

1. **User Signup** - Creates a new user account in Auth Service
2. **Baseline Login** - Performs successful login to establish normal behavior
3. **Attack Simulation** - Performs 12 failed login attempts within 5 minutes
4. **Fraud Detection** - MCP Server analyzes events and calculates risk score
5. **Email Notification** - Verifies email notification log appears when risk_score >= 0.7

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+
- All services defined in `auth_platform/docker-compose.yml`

## Installation

Install test dependencies:

```bash
cd mcp_server
pip install -r requirements-test.txt
```

## Running the Tests

### Run all E2E tests:

```bash
pytest tests/test_e2e_email_notification.py -v -s --log-cli-level=INFO
```

### Run specific test:

```bash
# Test complete signup to email notification flow
pytest tests/test_e2e_email_notification.py::test_e2e_signup_to_email_notification -v -s

# Test IP change fraud detection
pytest tests/test_e2e_email_notification.py::test_e2e_ip_change_fraud_detection -v -s
```

## What the Test Verifies

### ✅ Authentication Flow
- User signup creates account successfully
- Login with correct credentials succeeds
- Login with wrong credentials fails with 401

### ✅ Event Logging
- Signup events are sent to MCP Server
- Login success events are logged
- Login failure events are logged
- All events contain proper metadata (user_id, username, timestamp, IP, user agent)

### ✅ Fraud Detection
- Multiple failed login attempts (11+) trigger high risk score (>= 0.7)
- Risk score calculation includes:
  - Failed login count in 5-minute window
  - IP address changes
  - User agent changes
- Fraud reason explains why risk is high

### ✅ Email Notification Logging
- High-risk events (risk_score >= 0.7) trigger email notification logs
- MCP Server logs contain: `⚠️ HIGH RISK EVENT DETECTED`
- MCP Server logs contain: `📧 EMAIL NOTIFICATION TRIGGER`
- Logs include username, risk score, and reason

### ✅ Data Integrity
- Events are properly stored in MCP database
- Fraud assessments are queryable via API
- Event counts match expected values

## Test Output Example

```
Step 1: Creating user account: e2e_test_user_1701234567
✓ User created successfully: user_id=123

Step 2: Performing successful login for e2e_test_user_1701234567
✓ Successful login completed

Step 3: Performing 12 failed login attempts to trigger fraud detection
  Failed login attempt 1/12
  Failed login attempt 2/12
  ...
  Failed login attempt 12/12
✓ Completed 12 failed login attempts

Step 4: Verifying fraud detection for user_id=123
✓ Fraud detected: risk_score=0.70, reason=Severe brute force attack detected (11 failed logins in 5 minutes)

Step 5: Verifying email notification log in MCP Server
✓ Found high risk event log: 2024-01-15 10:36:40 - routes.ingest - WARNING - ⚠️ HIGH RISK EVENT DETECTED...
✓ Found email notification log: 2024-01-15 10:36:40 - routes.ingest - WARNING - 📧 EMAIL NOTIFICATION TRIGGER...
✓ Email notification logging verified successfully

Step 6: Verifying event details in MCP Server
  Signup events: 1
  Login success events: 1
  Login failure events: 12
✓ All event details verified

======================================================================
END-TO-END TEST SUMMARY
======================================================================
✓ User signup successful: e2e_test_user_1701234567 (user_id=123)
✓ Baseline login established
✓ 12 failed login attempts performed
✓ Fraud detection triggered: risk_score=0.70
✓ Email notification logged in MCP Server
✓ All events properly stored and analyzed
======================================================================
✅ END-TO-END TEST PASSED
======================================================================
```

## Troubleshooting

### Services fail to start

If Docker services don't start within 30 seconds:

```bash
# Check if ports are already in use
lsof -i :8000
lsof -i :8001

# Manually start services
cd auth_platform
docker-compose up -d

# Check logs
docker-compose logs auth-service
docker-compose logs mcp-server
```

### Test fails to find email notification logs

The test looks for specific log patterns. Ensure:

1. MCP Server logging is configured (check `mcp_server/main.py`)
2. Log level is set to WARNING or lower (check `mcp_server/config.py`)
3. Fraud threshold is 0.7 (check `mcp_server/.env`)

### Events not appearing in MCP Server

Check Auth Service configuration:

```bash
# Verify MCP_SERVER_URL is set correctly
docker exec auth_platform-auth-service-1 env | grep MCP_SERVER_URL

# Should output: MCP_SERVER_URL=http://mcp-server:8001
```

## Architecture

```
┌─────────────────┐
│   Test Client   │
└────────┬────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌─────────────────┐
│  Auth Service   │                  │   MCP Server    │
│   (Port 8000)   │◄─────────────────│   (Port 8001)   │
└────────┬────────┘   Event Stream   └────────┬────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌─────────────────┐
│   Auth DB       │                  │    MCP DB       │
│  (SQLite)       │                  │   (SQLite)      │
└─────────────────┘                  └─────────────────┘
```

## Test Scenarios

### Scenario 1: Brute Force Attack Detection
- **Trigger**: 11+ failed login attempts in 5 minutes
- **Expected Risk Score**: 0.70 (Severe brute force)
- **Email Notification**: YES

### Scenario 2: IP Address Change
- **Trigger**: Login from different IP than previous successful login
- **Expected Risk Score**: 0.20 (IP change)
- **Email Notification**: NO (below threshold)

### Scenario 3: Combined Factors
- **Trigger**: Failed logins + IP change + User agent change
- **Expected Risk Score**: 0.70+ (Combined risk)
- **Email Notification**: YES

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd mcp_server
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run E2E tests
        run: |
          cd mcp_server
          pytest tests/test_e2e_email_notification.py -v
```

## Future Enhancements

- [ ] Test 2FA fraud detection scenarios
- [ ] Test password reset fraud patterns
- [ ] Test account lockout after multiple failures
- [ ] Test alert consolidation across multiple events
- [ ] Test BAML agent integration (when enabled)
- [ ] Performance testing with concurrent users
- [ ] Test email notification rate limiting

## Related Documentation

- [MCP Server README](../README.md)
- [Fraud Detection Implementation](../IMPLEMENTATION_SUMMARY.md)
- [Email Notification Migration](../ALERT_TO_EMAIL_MIGRATION.md)
- [API Testing with Insomnia](../INSOMNIA_IMPORT_GUIDE.md)
