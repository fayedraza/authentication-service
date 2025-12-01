# GitHub Actions CI/CD Workflows

This directory contains automated workflows for continuous integration and deployment.

## Workflows

### 1. `ci.yml` - Basic CI Pipeline
**Triggers:** Push and Pull Requests to `main` and `develop` branches

**Steps:**
1. Checkout code
2. Set up Python environment
3. Build Docker images
4. Start services with Docker Compose
5. Wait for services to be ready
6. Run unit tests
7. Run end-to-end tests
8. Show logs on failure
9. Clean up

**Duration:** ~5-8 minutes

### 2. `full-ci.yml` - Comprehensive CI Pipeline
**Triggers:** Push and Pull Requests to `main` and `develop` branches

**Jobs:**

#### Lint Job
- Code formatting check (Black)
- Import sorting check (isort)
- Linting (Flake8)
- Security scanning (Bandit)

#### Unit Tests Job
- Runs isolated unit tests
- Fast feedback on code changes

#### Integration Tests Job
- Builds and starts all services
- Runs end-to-end tests
- Tests fraud detection and email notification logging
- Verifies complete user flows

#### Build Check Job
- Validates Docker images build successfully
- Reports image sizes

**Duration:** ~10-15 minutes

## Local Testing

You can run the same tests locally that run in CI:

### Quick Test
```bash
# Start services
cd auth_platform
docker compose up -d

# Wait for services
sleep 10

# Run tests
cd ../mcp_server
pytest tests/test_e2e_simple.py -v -s

# Cleanup
cd ../auth_platform
docker compose down
```

### Full Test Suite
```bash
# Lint
black --check mcp_server/ auth_platform/
flake8 mcp_server/ auth_platform/ --max-line-length=120

# Unit tests
cd mcp_server
pytest tests/test_fraud_detector.py -v

# Integration tests
cd ../auth_platform
docker compose up -d
sleep 10
cd ../mcp_server
pytest tests/test_e2e_simple.py -v -s
cd ../auth_platform
docker compose down
```

## CI/CD Best Practices

### What Gets Tested
✅ Code formatting and style
✅ Security vulnerabilities
✅ Unit tests (fast, isolated)
✅ Integration tests (full system)
✅ Docker image builds
✅ Service health checks
✅ Email notification logging
✅ Fraud detection logic

### What Doesn't Get Tested
❌ Manual UI testing
❌ Performance/load testing
❌ Production deployment
❌ Database migrations (future work)

## Troubleshooting CI Failures

### Services Won't Start
- Check Docker image build logs
- Verify docker-compose.yml syntax
- Check for port conflicts
- Review service logs in workflow output

### Tests Fail
- Check if services are healthy
- Review test logs
- Verify test data and expectations
- Check for timing issues (add more wait time)

### Timeout Issues
- Increase wait times in workflow
- Check service startup logs
- Verify health check endpoints

## Adding New Tests

1. **Unit Tests**: Add to `mcp_server/tests/test_*.py`
2. **Integration Tests**: Add to `mcp_server/tests/test_e2e_*.py`
3. **Update Workflow**: Add test command to `ci.yml` if needed

## Monitoring CI

- View workflow runs: GitHub → Actions tab
- Check build status badge (add to main README)
- Review failed runs for patterns
- Monitor test execution times

## Future Enhancements

- [ ] Add code coverage reporting
- [ ] Deploy to staging on successful builds
- [ ] Run performance benchmarks
- [ ] Add database migration tests
- [ ] Implement blue-green deployments
- [ ] Add Slack/email notifications for failures
