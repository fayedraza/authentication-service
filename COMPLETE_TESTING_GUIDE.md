# Complete End-to-End Testing Guide

## 📦 Import the Complete Collection

**File**: `complete-insomnia-collection.json`

1. Open Insomnia
2. Application Menu → Import/Export → Import Data → From File
3. Select `complete-insomnia-collection.json`
4. You'll see: **"Complete Auth + MCP Platform"** workspace

## 📚 What's Included

### 11 Folders with 30+ Requests:

1. **Auth - Registration** (1 request)
2. **Auth - Login Flow** (3 requests)
3. **Auth - 2FA Management** (2 requests)
4. **Auth - Password Reset** (2 requests)
5. **Auth - Event Logs** (2 requests)
6. **MCP - Health Checks** (2 requests)
7. **MCP - Event Ingestion** (3 requests)
8. **MCP - Event Queries** (3 requests)
9. **MCP - Fraud Detection** (3 requests)
10. **MCP - Alert Management** (4 requests)
11. **Test Scenarios** (3 requests)

## 🎯 Complete Testing Flow

### Phase 1: User Registration & Login

#### Step 1: Register a New User
**Folder**: 1. Auth - Registration
**Request**: Register New User

```json
{
  "username": "testuser",
  "first_name": "Test",
  "last_name": "User",
  "email": "test@example.com",
  "password": "SecurePass123!",
  "tier": "dev"
}
```

✅ **Expected**: User created with 2FA automatically enrolled

#### Step 2: Login (Password)
**Folder**: 2. Auth - Login Flow
**Request**: Login Step 1 (Password)

```json
{
  "username": "testuser",
  "password": "SecurePass123!"
}
```

✅ **Expected**: Returns `requires_2fa: true`

#### Step 3: Complete 2FA
**Folder**: 2. Auth - Login Flow
**Request**: Login Step 2 (2FA Bypass)

```json
{
  "username": "testuser",
  "code": "000000"
}
```

✅ **Expected**: Returns JWT token
📝 **Action**: Copy the `access_token` and paste it in Environment → `jwt_token`

---

### Phase 2: View Auth Events

#### Step 4: Check Event Logs
**Folder**: 5. Auth - Event Logs
**Request**: Get All Event Logs

✅ **Expected**: See `login_success`, `2fa_success`, `registration` events

---

### Phase 3: MCP Server Monitoring

#### Step 5: Verify MCP is Running
**Folder**: 6. MCP - Health Checks
**Request**: MCP Health Check

✅ **Expected**: `{"status": "healthy"}`

#### Step 6: Check Events in MCP
**Folder**: 8. MCP - Event Queries
**Request**: Get All Events

✅ **Expected**: See events from Auth Service with fraud analysis

---

### Phase 4: Test Fraud Detection

#### Step 7: Simulate Brute Force Attack
**Folder**: 11. Test Scenarios
Run these 3 requests in order:
1. Brute Force Attack (1/3)
2. Brute Force Attack (2/3)
3. Brute Force Attack (3/3)

✅ **Expected**: Each returns `event_id`

#### Step 8: Check Fraud Assessments
**Folder**: 9. MCP - Fraud Detection
**Request**: Get High Risk Events

✅ **Expected**: See events with `risk_score > 0.7`

#### Step 9: Check Generated Alerts
**Folder**: 10. MCP - Alert Management
**Request**: Get Open Alerts

✅ **Expected**: See alert for user_id=999 with status="open"

---

### Phase 5: Alert Management

#### Step 10: Update Alert Status
**Folder**: 10. MCP - Alert Management
**Request**: Update Alert Status

1. Copy an `alert_id` from previous step
2. Replace `ALERT_ID_HERE` in the URL
3. Send request with `{"status": "reviewed"}`

✅ **Expected**: Alert status updated

---

## 🔄 Complete Integration Test Flow

Run these in order to test the full system:

### 1. Register → Login → Check Events
```
1. Register New User
2. Login Step 1 (Password)
3. Login Step 2 (2FA Bypass)
4. Get All Event Logs (Auth)
5. Get All Events (MCP)
```

### 2. Failed Login → Fraud Detection → Alert
```
1. Failed Login (Wrong Password) - Run 3 times
2. Get High Risk Events
3. Get Open Alerts
4. Update Alert Status
```

### 3. Password Reset Flow
```
1. Request Password Reset
2. Check logs for token
3. Confirm Password Reset (with token)
4. Get All Event Logs
```

---

## 🌐 Environment Variables

The collection uses these variables:

- `auth_url`: http://localhost:8000 (Auth Service)
- `mcp_url`: http://localhost:8001 (MCP Server)
- `jwt_token`: Paste your JWT token here after login

**To update**:
1. Click environment dropdown (top left)
2. Select "Base Environment"
3. Edit values

---

## 📊 What to Look For

### Successful Login
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "username": "testuser",
    "email": "test@example.com"
  }
}
```

### Event with Fraud Analysis
```json
{
  "id": "550e8400-...",
  "user_id": 123,
  "event_type": "login_success",
  "risk_score": 0.0,
  "fraud_reason": "Normal authentication pattern",
  "analyzed_at": "2024-01-15T10:30:01Z"
}
```

### High Risk Alert
```json
{
  "id": "alert-550e8400-...",
  "user_id": 999,
  "risk_score": 0.85,
  "status": "open",
  "reason": "Multiple failed login attempts detected",
  "event_ids": ["event1", "event2", "event3"]
}
```

---

## 🐛 Troubleshooting

### "Connection refused" on Auth Service
```bash
docker compose ps
# Check if auth-service is running
docker compose up -d auth-service
```

### "Connection refused" on MCP Server
```bash
docker compose ps
# Check if mcp-server is running
docker compose up -d mcp-server
```

### No events showing in MCP
- Check Auth Service logs: `docker compose logs auth-service`
- Verify `MCP_PUSH_ENABLED=true` in Auth Service
- Check MCP Server logs: `docker compose logs mcp-server`

### JWT token expired
- Run Login flow again (Steps 2-3)
- Copy new token to environment variable

---

## 🎯 Quick Test Checklist

- [ ] Register user
- [ ] Login with password
- [ ] Complete 2FA
- [ ] View event logs in Auth Service
- [ ] View events in MCP Server
- [ ] Simulate failed logins (3x)
- [ ] Check fraud assessments
- [ ] Verify alert generated
- [ ] Update alert status
- [ ] Test password reset flow

---

## 📝 Notes

- **Local bypass code**: `000000` (works in dev mode)
- **Default ports**: Auth=8000, MCP=8001
- **Event types**: `login_success`, `login_failure`, `2fa_success`, `2fa_failure`, `password_reset`, etc.
- **Risk thresholds**: High (>0.7), Medium (0.4-0.7), Low (<0.4)

---

## 🚀 Next Steps

After testing manually:
1. Automate with test scripts
2. Set up monitoring dashboards
3. Configure real 2FA (not bypass)
4. Enable BAML AI fraud detection
5. Add alert notifications (email/Slack)
