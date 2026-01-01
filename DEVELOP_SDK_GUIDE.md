# Developer Guide: Integrating with Auth Service

This guide is intended for developers building SDKs, modules, or external applications that need to interface with the Authentication Service.

## Base URL
All requests should be made to the Auth Platform service.
- **Local Development**: `http://localhost:8000`
- **Docker Network**: `http://auth_platform:8000`

## Authentication Flow

### 1. User Registration
Create a new user account.


- **Endpoint**: `POST /auth/register`
- **Content-Type**: `application/json`
- **Payload**:
  ```json
  {
    "username": "jdoe",
    "password": "securepassword123",
    "email": "jdoe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "tier": "free"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "id": 1,
    "username": "jdoe",
    "email": "jdoe@example.com",
    "is_active": true,
    "tier": "free",
    "created_at": "2024-01-01T00:00:00.000000"
  }
  ```

### 2. Login (Token Acquisition)
Authenticate a user and retrieve an access token.

- **Endpoint**: `POST /auth/login`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Payload**:
  - `username`: `jdoe`
  - `password`: `securepassword123`
- **Response**: `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "requires2fa": false
  }
  ```
  *Note: If `requires2fa` is true, you must proceed to the 2FA verify step using the `2fa_token` provided.*

### 3. Password Reset Request
Initiate a password reset flow (sends email/token).

- **Endpoint**: `POST /auth/password-reset/request`
- **Content-Type**: `application/json`
- **Payload**:
  ```json
  {
    "email": "jdoe@example.com"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "message": "If the email exists, a reset token has been sent."
  }
  ```

### 4. Password Reset Confirm
Complete the password reset using the token.

- **Endpoint**: `POST /auth/password-reset/confirm`
- **Content-Type**: `application/json`
- **Payload**:
  ```json
  {
    "token": "reset_token_received_via_email",
    "new_password": "newSecurePassword456"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "message": "Password successfully reset."
  }
  ```

## Working with Headers

Once you have the `access_token`, include it in the `Authorization` header for all protected endpoints:

```http
Authorization: Bearer <access_token>
```

## Future Python SDK (Concept)

If you are building a Python client, the structure might look like this:

```python
from auth_sdk import AuthClient

client = AuthClient(base_url="http://localhost:8000")

# Register
user = client.register(
    username="jdoe",
    password="password123",
    email="j@example.com"
)

# Login
token_data = client.login(username="jdoe", password="password123")
access_token = token_data.access_token

# Authenticated Request
profile = client.get_profile(token=access_token)
```
