# GitHub Actions CI/CD Workflows

This directory contains automated workflows for continuous integration and deployment.

## Workflows

### `ci.yml` - Full CI Pipeline
**Triggers:** Push and Pull Requests to `main` and `develop` branches

**Jobs:**

#### Lint and Security Checks Job
- **Secret Detection**: Uses `detect-secrets` to scan for new secrets against baseline
- **Code Formatting**: Black formatting check
- **Import Sorting**: isort check
- **Linting**: Flake8 for code quality
- **Security Scanning**: Bandit for security vulnerabilities
- **Fast Feedback**: Runs first to catch issues early

#### Unit Tests Job
- Runs isolated unit tests
- Fast feedback on code changes
- No external dependencies

#### Integration Tests Job
- Builds and starts all services with Docker Compose
- Runs integration tests and end-to-end tests
- Tests fraud detection and email notification logging
- Verifies complete user flows
- Depends on lint and unit tests passing first

#### Build Check Job
- Validates Docker images build successfully
- Reports image sizes
- Runs independently to verify build process

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
✅ **Secret Detection** (detect-secrets baseline check)
✅ **Security Vulnerabilities** (Bandit)
✅ **Code Quality** (Black, isort, Flake8)
✅ **Unit Tests** (fast, isolated)
✅ **Integration Tests** (full system)
✅ **Docker Image Builds**
✅ **Service Health Checks**
✅ **Email Notification Logging**
✅ **Fraud Detection Logic**

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
