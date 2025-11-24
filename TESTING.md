# Authentication Platform - Testing Guide

## Quick Start

### Start the Services

```bash
docker compose up -d
```

### View Logs

```bash
docker compose logs -f auth_platform
```

## API Testing

### Using cURL

All examples use `python -m json.tool` to prettify JSON output.

#### 1. Register a New User

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "password": "SecurePass123!",  # pragma: allowlist secret
    "tier": "dev"
  }' | python -m json.tool
```

**Response includes:**
- `access_token`: JWT token
- `otpauth_uri`: QR code URI for 2FA setup
- `requires_2fa_setup`: true (2FA is auto-enabled)

#### 2. Login (Step 1 - Password)

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"  # pragma: allowlist secret
  }' | python -m json.tool
```

**Response:**
- `requires2fa`: true
- `message`: "Please enter the 6-digit code from your authenticator app"

#### 3. Login (Step 2 - 2FA Verification)

**For local development, use bypass code:**

```bash
curl -X POST http://localhost:8000/2fa/verify \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "code": "000000"
  }' | python -m json.tool
```

**For production, use actual TOTP code from authenticator app:**

```bash
curl -X POST http://localhost:8000/2fa/verify \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "code": "123456"
  }' | python -m json.tool
```

#### 4. Check 2FA Status

```bash
# Replace YOUR_TOKEN with the JWT from login/register
curl -X GET http://localhost:8000/2fa/status \
  -H "Authorization: Bearer YOUR_TOKEN" | python -m json.tool
```

#### 5. Disable 2FA

```bash
curl -X POST http://localhost:8000/2fa/disable \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"  # pragma: allowlist secret
  }' | python -m json.tool
```

#### 6. Re-enroll in 2FA

```bash
curl -X POST http://localhost:8000/2fa/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"  # pragma: allowlist secret
  }' | python -m json.tool
```

#### 7. Password Reset Request

```bash
curl -X POST http://localhost:8000/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }' | python -m json.tool
```

**Note:** In dev mode, the reset token is printed to the container logs.

#### 8. Password Reset Confirm

```bash
# Replace RESET_TOKEN with token from logs
curl -X POST http://localhost:8000/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "RESET_TOKEN",
    "new_password": "NewSecurePass123!"  # pragma: allowlist secret
  }' | python -m json.tool
```

#### 9. Create Support Ticket

```bash
# Replace YOUR_TOKEN with the JWT from login/register
curl -X POST http://localhost:8000/support/ticket \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Login Issue",
    "description": "I cannot log in to my account"
  }' | python -m json.tool
```

#### 10. List Support Tickets

```bash
# Replace YOUR_TOKEN with the JWT from login/register
curl -X GET http://localhost:8000/support/tickets \
  -H "Authorization: Bearer YOUR_TOKEN" | python -m json.tool
```

### Dev Monitor Endpoints (DEV_MODE only)

#### View Authentication Event Logs

```bash
# Get last 10 events
curl http://localhost:8000/dev/event-logs?limit=10 | python -m json.tool

# Filter by event type
curl http://localhost:8000/dev/event-logs?event_type=login_success | python -m json.tool

# Filter by user ID
curl http://localhost:8000/dev/event-logs?user_id=1 | python -m json.tool

# Combine filters
curl "http://localhost:8000/dev/event-logs?event_type=2fa_failure&user_id=1&limit=5" | python -m json.tool
```

**Event Types:**
- `login_success`
- `login_failure`
- `2fa_success`
- `2fa_failure`
- `password_reset`

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

Key environment variables for testing:

- `DEV_MODE=true` - Enables dev monitor endpoints
- `ENVIRONMENT=local` - Enables local development features (2FA bypass with "000000")
- `DATABASE_URL` - Database connection string

## Testing Tips

1. **View container logs** to see 2FA otpauth URIs and password reset tokens:
   ```bash
   docker compose logs -f auth_platform
   ```

2. **Reset the database** by removing the volume:
   ```bash
   docker compose down -v
   docker compose up -d
   ```

3. **Test 2FA locally** without an authenticator app using the bypass code `000000`

4. **Monitor authentication events** using the `/dev/event-logs` endpoint

5. **Use the Swagger UI** at http://localhost:8000/docs for interactive testing
