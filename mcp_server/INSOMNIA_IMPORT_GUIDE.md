# Insomnia Import Guide

## ✅ The collection is now properly formatted for Insomnia!

## Step-by-Step Import Instructions

### 1. Open Insomnia
- Launch the Insomnia application on your computer

### 2. Import the Collection
- Click on **"Create"** button (or the dropdown arrow next to it)
- Select **"Import From"** → **"File"**
- Navigate to: `mcp_server/insomnia-collection.json`
- Click **"Open"** or **"Import"**

### 3. Verify Import
You should now see:
- **Workspace**: "MCP Server API"
- **5 Folders**:
  1. Health Checks (2 requests)
  2. Event Ingestion (3 requests)
  3. Event Queries (2 requests)
  4. Fraud Assessments (2 requests)
  5. Alert Management (2 requests)

### 4. Set Up Environment (Already Configured!)
The collection includes a base environment with:
- `base_url`: http://localhost:8001

This should work automatically with `{{ _.base_url }}` in the requests.

## Testing the Requests

### Test 1: Health Check ✅
1. Click on folder: **"1. Health Checks"**
2. Click on: **"Health Check"**
3. You should see:
   - Method: `GET`
   - URL: `{{ _.base_url }}/health`
4. Click **"Send"**
5. ✅ Expected response:
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-11-30T..."
   }
   ```

### Test 2: Ingest Login Success 📥
1. Click on folder: **"2. Event Ingestion"**
2. Click on: **"Ingest Login Success"**
3. You should see:
   - Method: `POST`
   - URL: `{{ _.base_url }}/mcp/ingest`
   - **Body tab**: JSON with user_id, username, etc.
4. Click **"Send"**
5. ✅ Expected response:
   ```json
   {
     "message": "Event accepted for processing",
     "event_id": "a9663c2f-...",
     "status": "accepted"
   }
   ```

### Test 3: Query Events 🔍
1. Click on folder: **"3. Event Queries"**
2. Click on: **"Get Events by User ID"**
3. You should see:
   - Method: `GET`
   - URL: `{{ _.base_url }}/mcp/events?user_id=123`
4. Click **"Send"**
5. ✅ Expected response: List of events with fraud analysis

## What Each Request Does

### 1. Health Checks
- **Health Check**: Verify service is running
- **Readiness Check**: Check database and BAML agent status

### 2. Event Ingestion
- **Ingest Login Success**: Send a normal login event (low risk)
- **Ingest Login Failure**: Send a failed login (for fraud testing)
- **Ingest 2FA Failure**: Send a failed 2FA attempt

### 3. Event Queries
- **Get All Events**: Retrieve all stored events
- **Get Events by User ID**: Filter events for user_id=123

### 4. Fraud Assessments
- **Get All Fraud Assessments**: See all fraud analysis with statistics
- **Get High Risk Events**: Filter for events with risk_score > 0.7

### 5. Alert Management
- **Get All Alerts**: Retrieve all security alerts
- **Get Open Alerts**: Filter for alerts with status="open"

## Customizing Requests

### Change User ID
In any request, you can edit the JSON body or URL parameters:
- Click on the request
- Go to the **Body** tab (for POST) or edit the **URL** (for GET)
- Change `user_id` to test different users

### Change Event Type
Valid event types:
- `login_success`
- `login_failure`
- `2fa_success`
- `2fa_failure`
- `password_reset`
- `password_reset_request`
- `account_locked`
- `account_unlocked`

### Add Query Parameters
For GET requests, you can add parameters to the URL:
- `?user_id=123`
- `?event_type=login_failure`
- `?min_risk_score=0.7`
- `?status=open`
- `?limit=50&offset=0`

## Troubleshooting

### "Could not send request" Error
**Check if servers are running:**
```bash
docker compose ps
```
Both `auth-service` and `mcp-server` should show "Up"

**Restart if needed:**
```bash
docker compose restart mcp-server
```

### "404 Not Found" Error
**Verify the URL:**
- Should be: `http://localhost:8001` (not 8000)
- Check the environment variable `base_url`

### Body Not Showing
**For POST requests:**
1. Click on the request
2. Look for the **"Body"** tab (next to Headers)
3. Select **"JSON"** from the dropdown
4. The JSON should appear in the text area

### Environment Variable Not Working
**If `{{ _.base_url }}` doesn't resolve:**
1. Click on the environment dropdown (top left)
2. Select **"Base Environment"**
3. Verify `base_url` is set to `http://localhost:8001`
4. Or manually replace `{{ _.base_url }}` with `http://localhost:8001` in the URL

## Quick Test Scenario

Run these in order to see the full workflow:

1. **Health Check** → Verify service is up
2. **Ingest Login Success** → Send normal event
3. **Get Events by User ID** → See the event stored
4. **Ingest Login Failure** (3 times) → Simulate attack
5. **Get High Risk Events** → See fraud detection
6. **Get Open Alerts** → See generated alerts

## Need Help?

If Insomnia still doesn't work:
1. Try the browser API docs: http://localhost:8001/docs
2. Use the Postman collection: `postman-collection.json`
3. Use curl commands from: `QUICK_TEST_GUIDE.md`

All three methods test the same API!
