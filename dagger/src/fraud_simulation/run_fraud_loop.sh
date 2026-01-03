#!/bin/bash

# Fraud Simulation Loop Runner
# Runs the Dagger pipeline repeatedly for a set duration

# Configuration
RUNTIME_MINUTES=5
INTERVAL_SECONDS=60
PROGRESS_FILE="fraud_simulation/results/loop_progress.txt"

# Automatically detect project root (one level up from script location)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"

# Check if venv exists, fallback to system python if not
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python3"
fi

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🔥 Starting Fraud Simulation Loop"
echo " 🏠 Root:     $PROJECT_ROOT"
echo " 🐍 Python:   $VENV_PYTHON"
echo " ⏰ Duration: $RUNTIME_MINUTES minutes"
echo " ⏱️  Interval: $INTERVAL_SECONDS seconds"
echo " 📂 Results:  fraud_simulation_reports/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clear previous iterations
echo "🧹 Clearing previous iteration results..."
rm -rf fraud_simulation_reports/iterations/*.json


# Calculate end time
END_TIME=$((SECONDS + RUNTIME_MINUTES * 60))
ITERATION=1

mkdir -p fraud_simulation_reports

while [ $SECONDS -lt $END_TIME ]; do
    CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$CURRENT_TIME] 🔄 Starting Iteration #$ITERATION..."

    # Run the Dagger pipeline using the detected root and python
    "$VENV_PYTHON" fraud_simulation/fraud_agent_pipeline.py

    if [ $? -eq 0 ]; then
        echo "[$CURRENT_TIME] ✅ Iteration #$ITERATION finished successfully."
    else
        echo "[$CURRENT_TIME] ❌ Iteration #$ITERATION failed. Check error logs."
    fi

    # Calculate remaining time
    REMAINING=$(( (END_TIME - SECONDS) / 60 ))
    echo "⏳ Time remaining: ~$REMAINING minutes"

    if [ $SECONDS -lt $END_TIME ]; then
        echo "💤 Sleeping for $INTERVAL_SECONDS seconds..."
        sleep $INTERVAL_SECONDS
    fi

    ITERATION=$((ITERATION + 1))
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " 🏁 Fraud Simulation Loop Complete"
echo " 📊 Final Summary: fraud_simulation_reports/summary.json"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
