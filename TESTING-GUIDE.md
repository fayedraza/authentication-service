# Testing Guide

This guide explains how to run tests locally and in CI/CD.

## Overview

We use **Docker Compose** for both local testing and CI/CD. This is the industry-standard approach that provides:
- ✅ Consistent environment (same locally and in CI)
- ✅ Simple setup (`docker compose up -d`)
- ✅ Fast test execution (containers stay running)
- ✅ Easy debugging (check logs with `docker logs`)
- ✅ Works reliably on macOS, Linux, and Windows
- ✅ No complex testcontainers configuration needed

## Local Testing

### Quick Start

```bash
# 1. Start services
cd auth_platform
docker compose up -d

# 2. Wait for services to be ready (10 seconds)
sleep 10

# 3. Run tests
cd ../mcp_server
pytest tests/test_e2e_simple.py -v -s

# 4. Stop services when done
cd ../auth_platform
docker compose down
```

### Running Specific Tests

```bash
# Unit tests only (fast)
cd mcp_server
pytest tests/test_fraud_detector.py -v

# Integration tests (requires services running)
cd auth_platform
docker compose up -d
sleep 10
cd ../mcp_server
pytest tests/test_e2e_simple.py -v -s

# Run with detailed logging
pytest tests/test_e2e_simple.py -v -s --log-cli-level=INFO
```

### Manual Testing with Insomnia/Postman

Use the provided Insomnia collections:
- `complete-insomnia-collection.json` - Full API testing
- `mcp_server/email-notification-insomnia.json` - Email notification testing

Import into Insomnia and test the APIs while services are running.

## Verifying Email Notifications

### Method 1: Via Logs

```bash
# Start services
cd auth_platform
docker compose up -d

# Send multiple failed login attempts
for i in {1..12}; do
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
  curl -X POST http://localhost:8001/mcp/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": 999,
      \"username\": \"test_user\",
      \"event_type\": \"login_failure\",
      \"timestamp\": \"$TIMESTAMP\",
      \"ip_address\": \"10.0.0.1\",
      \"user_agent\": \"Test/1.0\"
    }"
  sleep 0.3
done

# Check logs for email notification
docker logs auth_platform-mcp-server-1 2>&1 | grep "📧 EMAIL NOTIFICATION"
```

### Method 2: Via API

```bash
# Query fraud assessments
curl "http://localhost:8001/mcp/fraud-assessments?user_id=999&sort_by=risk_score&sort_order=desc" | jq
```

Look for entries with `risk_score >= 0.7` and `email_notification: true`.

## CI/CD Testing

### GitHub Actions

Tests run automatically on every push and pull request to `main` or `develop` branches.

**Workflows:**
- `.github/workflows/ci.yml` - Basic CI (5-8 minutes)
- `.github/workflows/full-ci.yml` - Full CI with linting (10-15 minutes)

**What gets tested:**
1. Code formatting and linting
2. Security scanning
3. Unit tests
4. Integration tests
5. Email notification logging
6. Docker image builds

**View results:**
- Go to GitHub → Actions tab
- Click on any workflow run
- Review logs and test results

### Local CI Simulation

Run the same tests that CI runs:

```bash
# Full CI simulation
cd auth_platform
docker compose build
docker compose up -d
sleep 15

# Check service health
curl http://localhost:8001/health
curl http://localhost:8000/docs

# Run tests
cd ../mcp_server
pytest tests/test_e2e_simple.py -v -s

# Test email notifications
for i in {1..12}; do
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
  curl -X POST http://localhost:8001/mcp/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": 999,
      \"username\": \"ci_test\",
      \"event_type\": \"login_failure\",
      \"timestamp\": \"$TIMESTAMP\",
      \"ip_address\": \"10.0.0.1\",
      \"user_agent\": \"CI/1.0\"
    }" > /dev/null 2>&1
  sleep 0.3
done

docker logs auth_platform-mcp-server-1 2>&1 | grep "📧 EMAIL NOTIFICATION"

# Cleanup
cd ../auth_platform
docker compose down -v
```

## Test Files

### Unit Tests
- `mcp_server/tests/test_fraud_detector.py` - Fraud detection logic tests

### Integration Tests
- `mcp_server/tests/test_e2e_simple.py` - End-to-end flow tests
  - User signup
  - Authentication
  - Failed login attempts
  - Fraud detection
  - Email notification verification

## Troubleshooting

### Services won't start

```bash
# Check if ports are in use
lsof -i :8000
lsof -i :8001

# View service logs
docker logs auth_platform-auth-service-1
docker logs auth_platform-mcp-server-1

# Rebuild images
cd auth_platform
docker compose build --no-cache
docker compose up -d
```

### Tests fail

```bash
# Ensure services are healthy
curl http://localhost:8001/health
curl http://localhost:8000/docs

# Check service logs
docker logs auth_platform-mcp-server-1 --tail 50
docker logs auth_platform-auth-service-1 --tail 50

# Restart services
cd auth_platform
docker compose restart
sleep 10
```

### Email notifications not appearing

```bash
# Verify fraud threshold (default: 0.7)
docker logs auth_platform-mcp-server-1 2>&1 | grep "FRAUD_THRESHOLD"

# Check if events are being ingested
curl "http://localhost:8001/mcp/events?limit=10" | jq

# Verify fraud analysis is running
docker logs auth_platform-mcp-server-1 2>&1 | grep "fraud analysis"

# Send enough failed attempts (need 11+ for risk_score >= 0.7)
# See "Verifying Email Notifications" section above
```

## Best Practices

### Before Committing

1. Run tests locally
2. Check service logs for errors
3. Verify email notifications work
4. Clean up containers

```bash
cd auth_platform
docker compose up -d
sleep 10
cd ../mcp_server
pytest tests/test_e2e_simple.py -v
cd ../auth_platform
docker compose down
```

### During Development

Keep services running and run tests multiple times:

```bash
# Start once
cd auth_platform
docker compose up -d

# Run tests many times
cd ../mcp_server
pytest tests/test_e2e_simple.py -v
# ... make code changes ...
pytest tests/test_e2e_simple.py -v
# ... make more changes ...
pytest tests/test_e2e_simple.py -v

# Stop when done
cd ../auth_platform
docker compose down
```

### Debugging Failed Tests

1. **Check service logs first**
   ```bash
   docker logs auth_platform-mcp-server-1 --tail 100
   docker logs auth_platform-auth-service-1 --tail 100
   ```

2. **Run tests with verbose logging**
   ```bash
   pytest tests/test_e2e_simple.py -v -s --log-cli-level=DEBUG
   ```

3. **Test APIs manually**
   - Use Insomnia collections
   - Check API responses
   - Verify data in database

4. **Restart services**
   ```bash
   docker compose restart
   sleep 10
   ```

## Performance

- **Unit tests**: < 1 second
- **Integration tests**: 30-60 seconds (with service startup)
- **Full CI pipeline**: 10-15 minutes

## Future Enhancements

- [ ] Add code coverage reporting
- [ ] Performance/load testing
- [ ] Database migration tests
- [ ] API contract testing
- [ ] Security penetration testing
