#!/bin/bash

# Configuration
API_URL="http://localhost:8001"
USER_ID=999
USERNAME="ai.test.user"

echo "🧪 Starting AI Fraud Detection Test..."
echo "Target: $API_URL"
echo "User: $USERNAME (ID: $USER_ID)"
echo "----------------------------------------"

# 1. Send legitimate login (Baseline)
echo "1️⃣  Sending legitimate login event..."
curl -s -X POST "$API_URL/mcp/ingest" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"username\": \"$USERNAME\",
    \"event_type\": \"login_success\",
    \"ip_address\": \"192.168.1.100\",
    \"user_agent\": \"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"metadata\": {}
  }" | jq .
echo ""
sleep 1

# 2. Simulate rapid failure attack (Brute force pattern)
echo "2️⃣  Simulating brute force attack (10 rapid failures)..."
for i in {1..10}; do
  echo "   Attempt $i..."
  curl -s -X POST "$API_URL/mcp/ingest" \
    -H "Content-Type: application/json" \
    -d "{
      \"user_id\": $USER_ID,
      \"username\": \"$USERNAME\",
      \"event_type\": \"login_failure\",
      \"ip_address\": \"10.0.0.$i\",
      \"user_agent\": \"Bot/1.0\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
      \"metadata\": {}
    }" | jq -r '.message'
  sleep 0.5
done

# 3. Check for Fraud Assessment
echo "----------------------------------------"
echo "3️⃣  Checking Fraud Assessment (The 'AI' Analysis)..."
sleep 2

RESPONSE=$(curl -s "$API_URL/mcp/fraud-assessments?user_id=$USER_ID&limit=1&sort_by=timestamp&order=desc")
RISK_SCORE=$(echo $RESPONSE | jq -r '.assessments[0].risk_score')
REASON=$(echo $RESPONSE | jq -r '.assessments[0].reason')

echo "📊 Analysis Result:"
echo "   Risk Score: $RISK_SCORE"
echo "   Reason: $REASON"

if (( $(echo "$RISK_SCORE > 0.7" | bc -l) )); then
  echo "✅ AI/Rule Engine successfully flagged this as HIGH RISK."
else
  echo "⚠️  Risk score low. System might be in training or rule thresholds not met."
fi
