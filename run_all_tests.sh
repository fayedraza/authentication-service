#!/bin/bash
set -e

echo "=================================================="
echo "   RUNNING ALL TESTS For Authentication Service (Backend + Frontend)"
echo "=================================================="

# 1. Auth Platform Tests
echo ""
echo ">>> [1/5] Running Auth Platform Unit Tests..."
cd auth_platform
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found in auth_platform"
    exit 1
fi

# Run tests
python -m pytest auth_platform_tests
RET_AUTH=$?
deactivate
cd ..

if [ $RET_AUTH -eq 0 ]; then
    echo "✅ Auth Platform Tests PASSED"
else
    echo "❌ Auth Platform Tests FAILED"
    exit 1
fi

# 2. MCP Server Tests
echo ""
echo ">>> [2/5] Running MCP Server Unit Tests..."
cd mcp_server
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found in mcp_server"
    exit 1
fi

python -m pytest tests/unit
RET_MCP_UNIT=$?

if [ $RET_MCP_UNIT -eq 0 ]; then
    echo "✅ MCP Unit Tests PASSED"
else
    echo "❌ MCP Unit Tests FAILED"
    # Don't exit yet, continue to others
fi

echo ""
echo ">>> [3/5] Running MCP Server Integration Tests..."
# Note: These require Docker socket access which may be restricted
set +e
python -m pytest tests/integration
RET_MCP_INT=$?
set -e

if [ $RET_MCP_INT -eq 0 ]; then
    echo "✅ MCP Integration Tests PASSED"
else
    echo "⚠️ MCP Integration Tests FAILED (Known issue with Docker socket in this env)"
fi

echo ""
echo ">>> [4/5] Running MCP Server E2E Tests..."
# These require the docker containers to be running (docker compose up)
python -m pytest tests/e2e/test_api_key_lifecycle.py \
                 tests/e2e/test_fraud_scenarios.py \
                 tests/e2e/test_e2e_simple.py \
                 tests/e2e/test_email_notifications_e2e.py \
                 tests/e2e/test_events_query_e2e.py \
                 tests/e2e/test_alerts_e2e.py \
                 tests/e2e/test_fraud_assessments_e2e.py \
                 tests/e2e/test_core_integration_e2e.py
RET_MCP_E2E=$?

deactivate
cd ..

echo ""
echo ">>> [5/5] Running Frontend Tests (Dev Portal UI)..."
cd dev-portal-ui/dev-portal-ui
if [ -d "node_modules" ]; then
    npm test -- --watchAll=false
    RET_FRONTEND=$?
else
    echo "Warning: node_modules not found. Running npm install..."
    npm install
    npm test -- --watchAll=false
    RET_FRONTEND=$?
fi
cd ../..

echo ""
echo "=================================================="
echo "                  FINAL REPORT                    "
echo "=================================================="
if [ $RET_AUTH -eq 0 ]; then echo "✅ Auth Platform Unit: PASSED"; else echo "❌ Auth Platform Unit: FAILED"; fi
if [ $RET_MCP_UNIT -eq 0 ]; then echo "✅ MCP Server Unit:    PASSED"; else echo "❌ MCP Server Unit:    FAILED"; fi
if [ $RET_MCP_INT -eq 0 ]; then echo "✅ MCP Integration:    PASSED"; else echo "⚠️ MCP Integration:    FAILED (Check Docker)"; fi
if [ $RET_MCP_E2E -eq 0 ]; then echo "✅ MCP E2E Scenarios:  PASSED"; else echo "❌ MCP E2E Scenarios:  FAILED"; fi
if [ $RET_FRONTEND -eq 0 ]; then echo "✅ Frontend UI Tests:  PASSED"; else echo "❌ Frontend UI Tests:  FAILED"; fi
echo "=================================================="
