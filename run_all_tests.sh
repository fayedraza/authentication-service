#!/bin/bash
set -e

echo "=================================================="
echo "   RUNNING ALL TESTS For Authentication Service"
echo "=================================================="

# Setup Logs
# Clean contents but preserve directory structure if possible
mkdir -p logs/
rm -rf logs/*
echo "Cleared previous AI response logs."

# --- PHASE 1: CORE TESTS (Run Once) ---
echo ""
echo "=================================================="
echo "          PHASE 1: CORE TESTS (Unit/UI)           "
echo "=================================================="

# 1. Auth Platform Unit Tests
echo ">>> [1/3] Running Auth Platform Unit Tests..."
cd auth_platform
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found in auth_platform"
    exit 1
fi
python -m pytest auth_platform_tests
RET_AUTH=$?
deactivate
cd ..

# 2. MCP Server Unit Tests
echo ""
echo ">>> [2/3] Running MCP Server Unit Tests..."
cd mcp_server
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found in mcp_server"
    exit 1
fi
python -m pytest tests/unit
RET_MCP_UNIT=$?
deactivate  # Deactivate mcp_server venv

echo ""
echo ">>> [3/3] Running Frontend Tests (Dev Portal UI)..."
cd ../dev-portal-ui/dev-portal-ui
if [ -d "node_modules" ]; then
    npm test -- --watchAll=false
    RET_FRONTEND=$?
else
    echo "Warning: node_modules not found. Running npm install..."
    npm install
    npm test -- --watchAll=false
    RET_FRONTEND=$?
fi
cd ../.. # Back to root

# Check Core Test Results
if [ $RET_AUTH -ne 0 ] || [ $RET_MCP_UNIT -ne 0 ] || [ $RET_FRONTEND -ne 0 ]; then
    echo "❌ Core Tests FAILED. Aborting."
    exit 1
fi
echo "✅ Core Tests PASSED."


# --- PHASE 2: AI VERIFICATION LOOP (Run Per Model) ---
echo ""
echo "=================================================="
echo "        PHASE 2: AI VERIFICATION LOOP             "
echo "=================================================="

MODELS=("groq" "gemini")
RET_GROQ=0
RET_GEMINI=0

# Activate MCP venv once for E2E tests (it will be used in loop)
cd mcp_server
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

for model in "${MODELS[@]}"; do
    echo ""
    echo "--------------------------------------------------"
    echo ">>> Testing AI Model: $model"
    echo "--------------------------------------------------"

    # Switch Model & Restart Containers
    export AI_MODEL=$model
    echo "Restarting containers with AI_MODEL=$model..."
    docker compose up -d auth_platform mcp-server

    echo "Waiting for services to stabilize..."
    sleep 10

    # 3. Run Verification Test
    # We run ONLY the single verification test to avoid rate limits (Gemini 15 RPM)
    # while still proving the model integration and generating a comparison log.
    echo "Running verification test..."
    set +e # Allow pytest to fail without exiting script immediately
    pytest tests/e2e/test_verification_single.py

    MODEL_RET=$?
    set -e

    if [ "$model" == "groq" ]; then
        RET_GROQ=$MODEL_RET
    else
        RET_GEMINI=$MODEL_RET
    fi

    if [ $MODEL_RET -eq 0 ]; then
        echo "✅ Tests passed for $model"
    else
        echo "❌ Tests failed for $model"
    fi
done

deactivate
cd ..

# --- PHASE 3: REPORTING ---
echo ""
echo "=================================================="
echo "                  FINAL REPORT                    "
echo "=================================================="
echo "Core Tests:          PASSED"
if [ $RET_GROQ -eq 0 ]; then echo "AI Model [groq]:      PASSED"; else echo "AI Model [groq]:      FAILED"; fi
if [ $RET_GEMINI -eq 0 ]; then echo "AI Model [gemini]:    PASSED"; else echo "AI Model [gemini]:    FAILED"; fi
echo "=================================================="

echo ""
echo "=================================================="
echo "             AI RESPONSE LOGS COMPARISON          "
echo "=================================================="

if [ -d "logs" ]; then
    # Groq Logs
    echo "--- GROQ LOGS ---"
    find logs/groq -name "*.log" 2>/dev/null | sort | while read logfile; do
        echo ">>> $logfile"
        cat "$logfile"
        echo ""
    done

    echo ""
    echo "--- GEMINI LOGS ---"
    find logs/gemini -name "*.log" 2>/dev/null | sort | while read logfile; do
        echo ">>> $logfile"
        cat "$logfile"
        echo ""
    done
fi
echo "=================================================="

# Exit with failure if any model failed
if [ $RET_GROQ -ne 0 ] || [ $RET_GEMINI -ne 0 ]; then
    exit 1
fi
