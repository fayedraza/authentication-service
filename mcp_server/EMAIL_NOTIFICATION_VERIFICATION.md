# Email Notification Verification Guide

## 🎯 Goal
Verify that the system correctly identifies when an email should be sent to a user about suspicious activity.

## 📝 How It Works

When a high-risk event is detected (risk_score > 0.7), the system logs:

1. **High Risk Detection**:
   ```
   ⚠️ HIGH RISK EVENT DETECTED: event_id=abc123, user_id=456,
   username=suspicious.user, risk_score=0.85,
   reason=Multiple failed login attempts detected
   ```

2. **Email Notification Trigger**:
   ```
   📧 EMAIL NOTIFICATION TRIGGER: Would send email to user suspicious.user
   about suspicious activity. Risk: 0.85 - Multiple failed login attempts detected
   ```

## ✅ Verification Methods

### Method 1: Automated Test Script

Run the test script:
```bash
cd mcp_server
python test_email_notification_logs.py
```

**What it does**:
- Sends 3 failed login attempts
- Triggers high-risk detection
- Shows fraud assessment results
- Tells you how to check logs

### Method 2: Manual Testing with Insomnia

1. **Import Collection**: `complete-insomnia-collection.json`

2. **Run Test Scenario**:
   - Folder: **11. Test Scenarios**
   - Run: **Brute Force Attack (1/3)**
   - Run: **Brute Force Attack (2/3)**
   - Run: **Brute Force Attack (3/3)**

3. **Check Logs**:
   ```bash
   docker compose logs mcp-server | grep "EMAIL NOTIFICATION"
   ```

### Method 3: Check Logs Directly

```bash
# View recent logs
docker compose logs mcp-server --tail=50

# Filter for email notifications
docker compose logs mcp-server | grep -E "(HIGH RISK|EMAIL)"

# Follow logs in real-time
docker compose logs -f mcp-server | grep "EMAIL"
```

## 📊 What You'll See

### Successful Detection:

```log
mcp-server-1  | WARNING:root:⚠️ HIGH RISK EVENT DETECTED: event_id=abc-123,
user_id=999, username=attack.target, risk_score=0.80,
reason=Multiple failed login attempts detected

mcp-server-1  | WARNING:root:📧 EMAIL NOTIFICATION TRIGGER: Would send email
to user attack.target about suspicious activity.
Risk: 0.80 - Multiple failed login attempts detected
```

### What This Means:
- ✅ System detected suspicious activity
- ✅ Risk score exceeded threshold (0.7)
- ✅ Email **would be sent** to user
- ✅ Ready for AI integration

## 🧪 Test Scenarios

### Scenario 1: Multiple Failed Logins
**Trigger**: 3+ failed login attempts in 5 minutes
**Expected Risk Score**: 0.8+
**Email**: YES ✅

### Scenario 2: IP Address Change
**Trigger**: Login from different IP shortly after previous login
**Expected Risk Score**: 0.2-0.4
**Email**: NO ❌ (below threshold)

### Scenario 3: Multiple Failed 2FA
**Trigger**: 3+ failed 2FA attempts in 5 minutes
**Expected Risk Score**: 0.9+
**Email**: YES ✅

### Scenario 4: Normal Login
**Trigger**: Successful login from known IP
**Expected Risk Score**: 0.0
**Email**: NO ❌

## 🔍 Verification Checklist

- [ ] MCP Server is running (`docker compose ps`)
- [ ] Send high-risk events (3 failed logins)
- [ ] Check logs for "HIGH RISK EVENT DETECTED"
- [ ] Check logs for "EMAIL NOTIFICATION TRIGGER"
- [ ] Verify risk_score > 0.7
- [ ] Verify username is included in log
- [ ] Verify reason is descriptive

## 📧 Email Notification Details

### What the log tells you:

```
📧 EMAIL NOTIFICATION TRIGGER: Would send email to user suspicious.user
about suspicious activity. Risk: 0.85 - Multiple failed login attempts detected
```

**Extracted Information**:
- **Recipient**: `suspicious.user`
- **Risk Level**: `0.85` (High)
- **Reason**: `Multiple failed login attempts detected`
- **Action**: Email would be sent

### Future AI Integration:

The AI will:
1. Query MCP Server for user's events
2. Analyze patterns and context
3. Generate personalized email content
4. Send email to user

**Example Email** (AI-generated):
```
Subject: Suspicious Activity Detected on Your Account

Hi suspicious.user,

We detected unusual activity on your account:
- 3 failed login attempts from different IP addresses
- Risk level: High (0.85/1.0)
- Time: 2024-01-15 12:00-12:02 UTC

If this was you, you can ignore this message.
If not, please secure your account immediately.

[Secure My Account Button]
```

## 🎯 Success Criteria

You've successfully verified email notifications if:

1. ✅ High-risk events trigger log messages
2. ✅ "EMAIL NOTIFICATION TRIGGER" appears in logs
3. ✅ Risk score is correctly calculated
4. ✅ Username is included for email recipient
5. ✅ Reason is clear and actionable

## 🚀 Next Steps

Once verified:
1. ✅ System correctly identifies when to email
2. ✅ Logs provide all necessary information
3. 🤖 Ready for AI integration
4. 📧 AI can generate and send personalized emails

---

**Note**: Currently, no actual emails are sent. The system only logs when an email **would** be sent. This allows you to verify the logic before implementing actual email delivery.
