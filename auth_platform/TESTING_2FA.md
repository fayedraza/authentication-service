# TOTP 2FA Manual Testing Guide

This document provides comprehensive manual testing instructions for the Time-based One-Time Password (TOTP) two-factor authentication feature.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Docker Setup](#docker-setup)
- [Test Scenarios](#test-scenarios)
  - [1. New User Enrollment](#1-new-user-enrollment)
  - [2. Login with 2FA](#2-login-with-2fa)
  - [3. Invalid Code Handling](#3-invalid-code-handling)
  - [4. Rate Limiting](#4-rate-limiting)
  - [5. Re-enrollment](#5-re-enrollment)
  - [6. Disable 2FA](#6-disable-2fa)
  - [7. Login Without 2FA](#7-login-without-2fa)
  - [8. Edge Cases](#8-edge-cases)
- [Troubleshooting](#troubleshooting)
- [Automated Testing](#automated-testing)

## Prerequisites

Before testing, ensure you have:

1. **Docker and Docker Compose** installed
   - Docker Desktop (macOS/Windows) or Docker Engine + Docker Compose (Linux)
   - Verify: `docker --version` and `docker-compose --version`

2. **Authenticator Application** on your mobile device or desktop
   - Google Authenticator (iOS/Android)
   - Microsoft Authenticator (iOS/Android)
   - Authy (iOS/Android/Desktop)
   - 1Password (with TOTP support)
   - Any RFC 6238 compliant TOTP app

3. **Web Browser** (Chrome, Firefox, Safari, or Edge)

4. **QR Code Scanner** (built into most authenticator apps)

## Docker Setup

### Starting the Services

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up --build
   ```

   This will start:
   - Backend API (FastAPI) on `http://localhost:8000`
   - Frontend UI (React) on `http://localhost:3000`

3. **Verify services are running**:
   - Backend API docs: http://localhost:8000/docs
   - Frontend UI: http://localhost:3000
   - Check logs for any errors

4. **View logs** (in separate terminal):
   ```bash
   # All services
   docker-compose logs -f

   # Backend only
   docker-compose logs -f auth_platform

   # Frontend only
   docker-compose logs -f dev-portal-ui
   ```

### Stopping the Services

```bash
# Stop services (Ctrl+C in the terminal running docker-compose)
# Or in another terminal:
docker-compose down

# Stop and remove volumes (clean slate):
docker-compose down -v
```

### Resetting the Database

If you need to start fresh:

```bash
# Stop services
docker-compose down -v

# Remove database file (if using local SQLite)
rm -f auth_platform/app.db

# Restart services
docker-compose up --build
```

## Test Scenarios

### 1. New User Enrollment

**Objective**: Verify that a new user can successfully enroll in 2FA.

**Steps**:

1. **Open the frontend**: Navigate to http://localhost:3000

2. **Register a new user** (if registration is available):
   - Click "Register" or "Sign Up"
   - Enter username: `testuser1`
   - Enter email: `testuser1@example.com`
   - Enter password: `SecurePass123!`  <!-- pragma: allowlist secret -->
   - Submit the form

   *Alternative*: Use an existing test user if registration is not available

3. **Login with credentials**:
   - Username: `testuser1`
   - Password: `SecurePass123!`

4. **Navigate to Account page**:
   - Click "Account" in the navigation menu

5. **Enroll in 2FA**:
   - Locate the "Enable 2FA" or "Enroll in 2FA" section
   - Enter your username: `testuser1`
   - Enter your password: `SecurePass123!`
   - Click "Enroll" or "Enable 2FA"

6. **Verify QR code displays**:
   - ✅ QR code should appear on the page
   - ✅ otpauth URI should be displayed as text
   - ✅ Instructions should be clear

7. **Check backend logs**:
   ```bash
   docker-compose logs auth_platform | grep otpauth
   ```
   - ✅ otpauth URI should be logged to console
   - Format: `otpauth://totp/AuthService:testuser1?secret=XXXXX&issuer=AuthService`

8. **Scan QR code with authenticator app**:
   - Open your authenticator app
   - Select "Add account" or "Scan QR code"
   - Point camera at QR code on screen
   - ✅ Account should be added with name "AuthService (testuser1)"

9. **Verify 2FA status**:
   - ✅ Page should show "2FA Enabled" status
   - ✅ Enrollment date/time may be displayed

**Expected Results**:
- QR code and URI displayed correctly
- otpauth URI logged to backend console
- Authenticator app successfully added account
- 2FA status shows as enabled

**Requirements Tested**: 1.1, 1.2, 1.3, 1.4, 1.5, 8.3

---

### 2. Login with 2FA

**Objective**: Verify that users with 2FA enabled must provide TOTP code during login.

**Steps**:

1. **Logout** (if currently logged in):
   - Click "Logout" in navigation menu
   - ✅ Should redirect to login page

2. **Enter credentials**:
   - Username: `testuser1`
   - Password: `SecurePass123!`
   - Click "Login"

3. **Verify TOTP prompt appears**:
   - ✅ TOTP code input field should appear
   - ✅ Message should indicate "Enter your 6-digit code"
   - ✅ Input field should be auto-focused
   - ✅ No JWT token should be issued yet

4. **Open authenticator app**:
   - Find the "AuthService (testuser1)" entry
   - Note the current 6-digit code

5. **Enter TOTP code**:
   - Type the 6-digit code into the input field
   - Click "Verify" or press Enter

6. **Verify successful login**:
   - ✅ Should redirect to Dashboard or authenticated area
   - ✅ JWT token should be stored in localStorage
   - ✅ User should see their account information

7. **Check backend logs**:
   ```bash
   docker-compose logs auth_platform | tail -20
   ```
   - ✅ Should see log entry for successful 2FA verification

**Expected Results**:
- TOTP prompt appears after password validation
- Valid TOTP code grants access
- JWT issued only after successful TOTP verification
- User navigated to authenticated area

**Requirements Tested**: 2.1, 2.2, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4

---

### 3. Invalid Code Handling

**Objective**: Verify that invalid TOTP codes are rejected with appropriate error messages.

**Steps**:

1. **Logout and login again**:
   - Username: `testuser1`
   - Password: `SecurePass123!`

2. **Enter incorrect TOTP code**:
   - Enter: `000000` (or any invalid code)
   - Click "Verify"

3. **Verify error message**:
   - ✅ Error message should appear: "Invalid TOTP code" or similar
   - ✅ Should remain on login page
   - ✅ No JWT token issued

4. **Clear error and try again**:
   - Start typing in the input field
   - ✅ Error message should clear
   - Enter correct code from authenticator app
   - ✅ Should successfully login

5. **Test with expired code**:
   - Logout and login again
   - Wait for TOTP code to change in authenticator app
   - Enter the OLD code (from previous 30-second window)
   - ✅ Should be rejected with error message

6. **Test with malformed input**:
   - Logout and login again
   - Enter: `abc123` (non-numeric)
   - ✅ Should show validation error or reject code
   - Enter: `12345` (only 5 digits)
   - ✅ Should show validation error or reject code

**Expected Results**:
- Invalid codes rejected with clear error messages
- Error messages clear when user starts typing
- Expired codes rejected
- Malformed input validated

**Requirements Tested**: 3.4, 4.5

---

### 4. Rate Limiting

**Objective**: Verify that rate limiting prevents brute force attacks on TOTP verification.

**Steps**:

1. **Logout and login**:
   - Username: `testuser1`
   - Password: `SecurePass123!`

2. **Enter incorrect code 5 times**:
   - Attempt 1: Enter `111111`, click Verify
   - Attempt 2: Enter `222222`, click Verify
   - Attempt 3: Enter `333333`, click Verify
   - Attempt 4: Enter `444444`, click Verify
   - Attempt 5: Enter `555555`, click Verify

3. **Verify rate limit error**:
   - ✅ After 5th attempt, should see error: "Too many failed attempts"
   - ✅ Error should include time remaining (e.g., "Try again in 15 minutes")
   - ✅ HTTP status should be 429

4. **Attempt 6th verification**:
   - Enter correct code from authenticator app
   - ✅ Should still be blocked with rate limit error
   - ✅ Correct code should NOT work during lockout

5. **Check backend logs**:
   ```bash
   docker-compose logs auth_platform | grep -i "rate limit"
   ```
   - ✅ Should see rate limit enforcement logs

6. **Wait for rate limit to reset** (15 minutes):
   - *Note*: For testing purposes, you may want to temporarily reduce the rate limit window in the code
   - After 15 minutes, try logging in again
   - Enter correct TOTP code
   - ✅ Should successfully login

7. **Verify rate limit is per-user**:
   - Create/use a second test user: `testuser2`
   - Enroll `testuser2` in 2FA
   - While `testuser1` is rate limited, login as `testuser2`
   - ✅ `testuser2` should be able to verify TOTP normally

**Expected Results**:
- 5 failed attempts trigger rate limit
- Rate limit blocks further attempts for 15 minutes
- Error message includes time remaining
- Rate limit is enforced per user
- Successful attempts don't count toward limit

**Requirements Tested**: 6.1, 6.2, 6.3, 6.4

---

### 5. Re-enrollment

**Objective**: Verify that users can re-enroll to generate a new TOTP secret.

**Steps**:

1. **Login as user with 2FA enabled**:
   - Username: `testuser1`
   - Password: `SecurePass123!`
   - Enter current TOTP code

2. **Navigate to Account page**:
   - Click "Account" in navigation

3. **Verify current 2FA status**:
   - ✅ Should show "2FA Enabled"
   - ✅ Should see "Re-enroll" or "Reset 2FA" button

4. **Click "Re-enroll 2FA"**:
   - ✅ Confirmation dialog should appear
   - ✅ Warning about invalidating old codes

5. **Confirm re-enrollment**:
   - Enter password: `SecurePass123!`
   - Click "Confirm" or "Re-enroll"

6. **Verify new QR code displays**:
   - ✅ New QR code should appear
   - ✅ New otpauth URI should be displayed
   - ✅ URI should have different secret than before

7. **Check backend logs**:
   ```bash
   docker-compose logs auth_platform | grep otpauth | tail -2
   ```
   - ✅ New otpauth URI should be logged
   - ✅ Secret should be different from initial enrollment

8. **Scan new QR code**:
   - Open authenticator app
   - Remove old "AuthService (testuser1)" entry
   - Scan new QR code
   - Add new account

9. **Test old code doesn't work**:
   - Logout
   - Login with username/password
   - Try to use code from OLD authenticator entry (if you kept it)
   - ✅ Should be rejected

10. **Test new code works**:
    - Enter code from NEW authenticator entry
    - ✅ Should successfully login

**Expected Results**:
- Re-enrollment generates new secret
- New QR code and URI displayed
- Old TOTP codes invalidated
- New TOTP codes work correctly

**Requirements Tested**: 7.1, 7.2, 7.3, 7.4

---

### 6. Disable 2FA

**Objective**: Verify that users can disable 2FA and return to password-only authentication.

**Steps**:

1. **Login as user with 2FA enabled**:
   - Username: `testuser1`
   - Password: `SecurePass123!`
   - Enter TOTP code

2. **Navigate to Account page**:
   - Click "Account" in navigation

3. **Locate "Disable 2FA" button**:
   - ✅ Button should be visible when 2FA is enabled

4. **Click "Disable 2FA"**:
   - ✅ Confirmation dialog should appear
   - ✅ Should prompt for password

5. **Enter password and confirm**:
   - Enter password: `SecurePass123!`
   - Click "Disable" or "Confirm"

6. **Verify 2FA disabled**:
   - ✅ Should show "2FA Disabled" status
   - ✅ "Enable 2FA" button should now be visible
   - ✅ "Disable 2FA" button should be hidden

7. **Check backend logs**:
   ```bash
   docker-compose logs auth_platform | grep -i "2fa disabled"
   ```
   - ✅ Should see log entry for 2FA disable event

8. **Logout and login**:
   - Logout
   - Login with username: `testuser1` and password: `SecurePass123!`
   - ✅ Should NOT see TOTP prompt
   - ✅ Should be logged in immediately after password validation
   - ✅ JWT should be issued without TOTP verification

9. **Verify TOTP codes no longer work**:
   - Logout
   - Try to access `/2fa/verify` endpoint directly with old code
   - ✅ Should return error (2FA not enabled)

**Expected Results**:
- 2FA can be disabled with password confirmation
- TOTP secret cleared from database
- Login no longer requires TOTP code
- User can re-enable 2FA later if desired

**Requirements Tested**: 7.1, 7.2, 7.3

---

### 7. Login Without 2FA

**Objective**: Verify that users without 2FA enabled can login normally.

**Steps**:

1. **Create or use a user without 2FA**:
   - Register new user: `testuser_no2fa`
   - Or use existing user who hasn't enrolled

2. **Login with credentials**:
   - Username: `testuser_no2fa`
   - Password: `SecurePass123!`
   - Click "Login"

3. **Verify immediate login**:
   - ✅ Should NOT see TOTP prompt
   - ✅ Should redirect directly to Dashboard
   - ✅ JWT should be issued immediately

4. **Verify 2FA status on Account page**:
   - Navigate to Account page
   - ✅ Should show "2FA Disabled" or "2FA Not Enabled"
   - ✅ Should see "Enable 2FA" button

**Expected Results**:
- Users without 2FA login with password only
- No TOTP prompt displayed
- JWT issued immediately after password validation

**Requirements Tested**: 2.3

---

### 8. Edge Cases

**Objective**: Test various edge cases and error conditions.

#### 8.1 Time Window Tolerance

**Steps**:
1. Login with username/password
2. Wait until TOTP code is about to expire (last 5 seconds)
3. Enter the current code just as it changes
4. ✅ Code should still be accepted (30-second tolerance)

**Requirements Tested**: 3.5

#### 8.2 Concurrent Login Attempts

**Steps**:
1. Open two browser windows/tabs
2. Login in both windows simultaneously
3. Enter TOTP codes in both
4. ✅ Both should work (no session conflicts)

#### 8.3 Password Change with 2FA Enabled

**Steps**:
1. Login with 2FA
2. Change password (if feature exists)
3. Logout and login with new password
4. ✅ 2FA should still be enabled
5. ✅ Same TOTP codes should work

#### 8.4 Enrollment with Wrong Password

**Steps**:
1. Navigate to Account page
2. Try to enroll with incorrect password
3. ✅ Should return 401 error
4. ✅ 2FA should not be enabled

**Requirements Tested**: 1.1

#### 8.5 Disable with Wrong Password

**Steps**:
1. Login with 2FA enabled
2. Try to disable 2FA with wrong password
3. ✅ Should return 401 error
4. ✅ 2FA should remain enabled

#### 8.6 Network Error Handling

**Steps**:
1. Stop backend service: `docker-compose stop auth_platform`
2. Try to enroll or verify TOTP in UI
3. ✅ Should show network error message
4. Restart backend: `docker-compose start auth_platform`
5. ✅ Should be able to retry successfully

#### 8.7 Clipboard Paste Support

**Steps**:
1. Login with username/password
2. Copy a 6-digit code: `123456`
3. Paste into TOTP input field
4. ✅ Should accept pasted input
5. ✅ Should validate and submit

**Requirements Tested**: 4.2

---

## Troubleshooting

### Services Won't Start

**Problem**: `docker-compose up` fails or services crash

**Solutions**:
1. Check if ports are already in use:
   ```bash
   lsof -i :8000  # Backend port
   lsof -i :3000  # Frontend port
   ```
2. Stop conflicting services or change ports in `docker-compose.yml`
3. Check Docker logs:
   ```bash
   docker-compose logs
   ```
4. Rebuild from scratch:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up
   ```

### QR Code Not Displaying

**Problem**: QR code doesn't appear after enrollment

**Solutions**:
1. Check browser console for JavaScript errors (F12 → Console)
2. Verify `qrcode.react` is installed:
   ```bash
   docker-compose exec dev-portal-ui npm list qrcode.react
   ```
3. Check network tab for failed API requests
4. Verify backend returned otpauth URI in response

### TOTP Codes Not Working

**Problem**: Valid codes from authenticator app are rejected

**Solutions**:
1. **Check time synchronization**:
   - TOTP relies on accurate time
   - Verify system time is correct on both server and device
   - On mobile: Settings → Date & Time → Set Automatically
   - On server:
     ```bash
     docker-compose exec auth_platform date
     ```
2. **Verify secret was saved**:
   - Check backend logs for enrollment confirmation
   - Query database to verify `totp_secret` is stored
3. **Check valid_window setting**:
   - Should be set to 1 (30-second tolerance)
   - Verify in `auth.py` or backend logs
4. **Try multiple codes**:
   - Wait for code to refresh in authenticator
   - Try the new code immediately

### Rate Limit Not Resetting

**Problem**: Still blocked after 15 minutes

**Solutions**:
1. Check server time:
   ```bash
   docker-compose exec auth_platform date
   ```
2. Verify rate limit logic in backend logs
3. Manually clear attempts from database:
   ```bash
   docker-compose exec auth_platform python -c "
   from auth_platform.auth_service.db import SessionLocal
   from auth_platform.auth_service.models import TOTPAttempt
   db = SessionLocal()
   db.query(TOTPAttempt).delete()
   db.commit()
   "
   ```
4. Restart services:
   ```bash
   docker-compose restart
   ```

### Frontend Not Connecting to Backend

**Problem**: API requests fail with CORS or network errors

**Solutions**:
1. Verify backend is running:
   ```bash
   curl http://localhost:8000/docs
   ```
2. Check `config.js` in frontend for correct API URL
3. Verify CORS settings in backend `main.py`
4. Check browser console for specific error messages
5. Try accessing API directly:
   ```bash
   curl -X POST http://localhost:8000/login \
     -H "Content-Type: application/json" \
     -d '{"username":"testuser1","password":"SecurePass123!"}'
   ```

### Database Issues

**Problem**: Database errors or data not persisting

**Solutions**:
1. Check if database file exists:
   ```bash
   ls -la auth_platform/app.db
   ```
2. Verify database permissions:
   ```bash
   docker-compose exec auth_platform ls -la /app/app.db
   ```
3. Reset database:
   ```bash
   docker-compose down -v
   rm -f auth_platform/app.db
   docker-compose up --build
   ```
4. Check database schema:
   ```bash
   docker-compose exec auth_platform python -c "
   from auth_platform.auth_service.db import engine
   from sqlalchemy import inspect
   inspector = inspect(engine)
   print(inspector.get_table_names())
   "
   ```

### Authenticator App Issues

**Problem**: Can't scan QR code or add account

**Solutions**:
1. **Manual entry**: Use the otpauth URI text instead of QR code
   - Copy the secret from URI: `secret=XXXXXXXXXXXXXXXX`
   - In authenticator app, choose "Enter key manually"
   - Enter account name: `AuthService (testuser1)`
   - Enter secret key
   - Select "Time-based"
2. **QR code too small**: Zoom in browser or take screenshot
3. **Try different authenticator app**: Some apps have better QR scanning
4. **Check QR code format**: Verify otpauth URI is valid:
   ```
   otpauth://totp/AuthService:username?secret=SECRET&issuer=AuthService
   ```

### Logs Not Showing otpauth URI

**Problem**: Can't find otpauth URI in backend logs

**Solutions**:
1. Increase log verbosity in backend
2. Check specific service logs:
   ```bash
   docker-compose logs auth_platform | grep -i otpauth
   ```
3. Verify logging is configured in `main.py` or `auth.py`
4. Check if logs are being written to file instead of console

---

## Automated Testing

While this document focuses on manual testing, automated tests are also available:

### Backend Unit Tests

Run backend tests with pytest:

```bash
# Inside Docker container
docker-compose exec auth_platform poetry run pytest -v

# Or locally (if Poetry installed)
cd auth_platform
poetry run pytest -v

# Run specific test file
poetry run pytest auth_platform_tests/test_2fa.py -v

# Run specific test
poetry run pytest auth_platform_tests/test_2fa.py::test_verify_rate_limiting -v
```

### Frontend Unit Tests

Run frontend tests with Jest:

```bash
# Inside Docker container
docker-compose exec dev-portal-ui npm test -- --watchAll=false

# Or locally (if npm installed)
cd dev-portal-ui/dev-portal-ui
npm test -- --watchAll=false

# Run specific test file
npm test -- src/__tests__/Login2FA.test.jsx --watchAll=false
```

### Test Coverage

Generate coverage reports:

```bash
# Backend coverage
cd auth_platform
poetry run pytest --cov=auth_platform --cov-report=html

# Frontend coverage
cd dev-portal-ui/dev-portal-ui
npm test -- --coverage --watchAll=false
```

---

## Additional Resources

- **TOTP RFC**: [RFC 6238](https://tools.ietf.org/html/rfc6238)
- **pyotp Documentation**: https://pyauth.github.io/pyotp/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Testing Library**: https://testing-library.com/react

---

## Feedback and Issues

If you encounter issues not covered in this guide:

1. Check backend logs: `docker-compose logs auth_platform`
2. Check frontend logs: `docker-compose logs dev-portal-ui`
3. Review browser console (F12 → Console)
4. Check network requests (F12 → Network)
5. Open an issue in the repository with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output
   - Screenshots if applicable

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Tested With**: Docker Compose v2.x, Python 3.10+, Node.js 14+
