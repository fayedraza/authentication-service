# Quick Test Guide - MCP Server

## ✅ Test Right Now with curl

Copy and paste these commands into your terminal:

### 1. Health Check
```bash
curl http://localhost:8001/health
```
**Expected:** `{"status":"healthy","timestamp":"..."}`

---

### 2. Ingest a Normal Login Event
```bash
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "username": "john.doe",
    "event_type": "login_success",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0",
    "timestamp": "2024-01-15T10:30:00Z",
    "metadata": {}
  }'
```
**Expected:** `{"message":"Event accepted for processing","event_id":"...","status":"accepted"}`

---

### 3. Query Events for That User
```bash
curl "http://localhost:8001/mcp/events?user_id=123"
```
**Expected:** List of events with `risk_score: 0.0` (low risk)

---

### 4. Simulate Brute Force Attack (Run 3 Times)
```bash
# First failed login
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 999,
    "username": "attack.target",
    "event_type": "login_failure",
    "ip_address": "10.0.0.1",
    "user_agent": "curl/7.68.0",
    "timestamp": "2024-01-15T12:00:00Z",
    "metadata": {}
  }'

# Second failed login
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 999,
    "username": "attack.target",
    "event_type": "login_failure",
    "ip_address": "10.0.0.2",
    "user_agent": "curl/7.68.0",
    "timestamp": "2024-01-15T12:01:00Z",
    "metadata": {}
  }'

# Third failed login
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 999,
    "username": "attack.target",
    "event_type": "login_failure",
    "ip_address": "10.0.0.3",
    "user_agent": "curl/7.68.0",
    "timestamp": "2024-01-15T12:02:00Z",
    "metadata": {}
  }'
```

---

### 5. Check for High Risk Events
```bash
curl "http://localhost:8001/mcp/fraud-assessments?user_id=999"
```
**Expected:** Events with higher `risk_score` (0.3+)

---

### 6. Check for Generated Alerts
```bash
curl "http://localhost:8001/mcp/alerts?user_id=999&status=open"
```
**Expected:** Alert with `risk_score > 0.7` if threshold was met

---

### 7. Get All Fraud Statistics
```bash
curl "http://localhost:8001/mcp/fraud-assessments"
```
**Expected:** Statistics showing total events, high/medium/low risk counts

---

## 🌐 Test with Browser (Interactive API Docs)

1. Open: **http://localhost:8001/docs**
2. You'll see Swagger UI with all endpoints
3. Click any endpoint (e.g., `POST /mcp/ingest`)
4. Click **"Try it out"**
5. Edit the JSON in the Request body
6. Click **"Execute"**
7. See the response below

This is the **easiest way** to test without Insomnia!

---

## 📱 Fix Insomnia Issue

If Insomnia shows "not found", try this:

### Option 1: Use the Browser API Docs Instead
- Go to http://localhost:8001/docs
- Much easier and works immediately!

### Option 2: Manually Create Requests in Insomnia

1. **Create New Request**
   - Click "+" → "HTTP Request"
   - Name it: "Health Check"

2. **Configure Request**
   - Method: `GET`
   - URL: `http://localhost:8001/health`
   - Click "Send"

3. **For POST Requests** (Event Ingestion)
   - Method: `POST`
   - URL: `http://localhost:8001/mcp/ingest`
   - Headers: Add `Content-Type: application/json`
   - Body: Select "JSON" and paste:
   ```json
   {
     "user_id": 123,
     "username": "test.user",
     "event_type": "login_success",
     "ip_address": "192.168.1.100",
     "user_agent": "Mozilla/5.0",
     "timestamp": "2024-01-15T10:30:00Z",
     "metadata": {}
   }
   ```

### Option 3: Try Postman Instead
I can create a Postman collection if you prefer!

---

## 🎯 Quick Test Scenarios

### Scenario A: Normal User
```bash
# Send normal login
curl -X POST http://localhost:8001/mcp/ingest \
  -H "Content-Type: application/json" \
  -d '{"user_id":100,"username":"normal.user","event_type":"login_success","ip_address":"192.168.1.1","user_agent":"Mozilla/5.0","timestamp":"2024-01-15T10:00:00Z","metadata":{}}'

# Check the event
curl "http://localhost:8001/mcp/events?user_id=100"
```
✅ Should show `risk_score: 0.0`

### Scenario B: Suspicious Activity
```bash
# Send 3 failed logins quickly
for i in 1 2 3; do
  curl -X POST http://localhost:8001/mcp/ingest \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":200,\"username\":\"hacker\",\"event_type\":\"login_failure\",\"ip_address\":\"10.0.0.$i\",\"user_agent\":\"curl\",\"timestamp\":\"2024-01-15T11:0$i:00Z\",\"metadata\":{}}"
done

# Check fraud assessment
curl "http://localhost:8001/mcp/fraud-assessments?user_id=200"
```
✅ Should show higher `risk_score`

---

## 💡 Pro Tip

**Use the Swagger UI at http://localhost:8001/docs** - it's the easiest way to test and you can see all the request/response schemas!
