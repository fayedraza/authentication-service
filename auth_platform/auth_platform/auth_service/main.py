from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from .db import get_db, init_db
from .models import User, PasswordResetToken, Ticket
from .schemas import (
    UserCreate,
    UserLogin,
    Token,
    RegistrationResponse,
    LoginStep1Response,
    EnrollRequest,
    EnrollResponse,
    TOTPVerifyRequest,
    TOTPDisableRequest,
    TOTPStatusResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    TicketCreate,
    TicketResponse,
)
from .auth import hash_password, verify_password, create_access_token, check_rate_limit, record_totp_attempt
from .utils.event_logger import log_auth_event
from .routes import dev_monitor
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, Optional
import os
import pyotp
from datetime import datetime, timedelta
import uuid
import jwt

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include dev monitor router
app.include_router(dev_monitor.router)

@app.on_event("startup")
def startup():
    init_db()

@app.post("/register", response_model=RegistrationResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email or username already exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if user.tier not in ("dev", "pro"):
        raise HTTPException(status_code=400, detail="Tier must be 'dev' or 'pro'")

    hashed_pw = hash_password(user.password)

    # Generate TOTP secret for automatic 2FA enrollment
    try:
        totp_secret = pyotp.random_base32()

        # Validate secret length (must be at least 16 characters)
        if len(totp_secret) < 16:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate secure TOTP secret"
            )

        new_user = User(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            password=hashed_pw,
            tier=user.tier,
            is_2fa_enabled=True,
            totp_secret=totp_secret
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Log enrollment event
        print(f"[2FA] Auto-enrollment during registration: user_id={new_user.id}, username={new_user.username}, timestamp={datetime.utcnow().isoformat()}")

        # Generate otpauth URI for QR code
        issuer = os.getenv("AUTH_SERVICE_ISSUER", "AuthService")
        totp = pyotp.TOTP(new_user.totp_secret)
        otpauth_uri = totp.provisioning_uri(name=new_user.username, issuer_name=issuer)

        # Log URI for dev tier testing
        print(f"[2FA] otpauth URI for {new_user.username}: {otpauth_uri}")

        token = create_access_token(new_user.username)
        return RegistrationResponse(
            access_token=token,
            token_type="bearer",
            otpauth_uri=otpauth_uri,
            requires_2fa_setup=True
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[2FA] Registration error for user {user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        ) from e

@app.post("/login", response_model=Union[Token, LoginStep1Response])
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password):
        # Log login failure event if user exists
        if user:
            log_auth_event("login_failure", user, request, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # If 2FA is enabled, require TOTP verification in a second step
    if user.is_2fa_enabled:
        # Log 2FA required event
        print(f"[2FA] Login requires 2FA: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")
        return LoginStep1Response(
            requires2fa=True,
            message="Please enter the 6-digit code from your authenticator app",
            username=user.username
        )

    # Log successful login without 2FA
    log_auth_event("login_success", user, request, db)
    print(f"[Login] Successful login: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")
    token = create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/2fa/enroll", response_model=EnrollResponse)
def enroll_2fa(payload: EnrollRequest, db: Session = Depends(get_db)):
    """
    Enroll user in TOTP 2FA or re-enroll with a new secret.
    Requires user/password authentication.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check if this is a re-enrollment
    is_reenrollment = user.totp_secret is not None and user.is_2fa_enabled

    # Generate new TOTP secret (always generate new for re-enrollment)
    try:
        new_secret = pyotp.random_base32()

        # Validate secret length (must be at least 16 characters)
        if len(new_secret) < 16:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate secure TOTP secret"
            )

        # Update user with new secret and enable 2FA
        user.totp_secret = new_secret
        user.is_2fa_enabled = True
        db.add(user)
        db.commit()
        db.refresh(user)

        # Log enrollment event
        if is_reenrollment:
            print(f"[2FA] Re-enrollment: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")
        else:
            print(f"[2FA] New enrollment: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")

        # Generate otpauth URI
        issuer = os.getenv("AUTH_SERVICE_ISSUER", "AuthService")
        totp = pyotp.TOTP(user.totp_secret)
        otpauth_uri = totp.provisioning_uri(name=user.username, issuer_name=issuer)

        # Log URI for dev tier testing
        print(f"[2FA] otpauth URI for {user.username}: {otpauth_uri}")

        return EnrollResponse(otpauth_uri=otpauth_uri)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[2FA] Enrollment error for user {payload.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enroll in 2FA"
        ) from e


@app.post("/2fa/verify", response_model=Token)
def verify_totp(payload: TOTPVerifyRequest, request: Request, db: Session = Depends(get_db)):
    from .auth import check_rate_limit, record_totp_attempt

    # Validate user exists and has 2FA enabled
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_2fa_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled for user")

    # Check for local development bypass
    is_local_env = os.getenv("ENVIRONMENT", "production").lower() in ["local", "development", "dev"]
    local_bypass_code = "000000"

    if is_local_env and payload.code == local_bypass_code:
        # Allow bypass in local environment with special code
        print(f"[2FA] Local bypass used: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")
        record_totp_attempt(user.id, True, db)
        log_auth_event("2fa_success", user, request, db)
        print(f"[Login] Successful login with 2FA (local bypass): user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")
        token = create_access_token(user.username)
        return {"access_token": token, "token_type": "bearer"}

    # Validate code format (must be 6 digits)
    if not payload.code or len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP code must be 6 digits")

    # Check rate limit before attempting verification
    is_rate_limited, minutes_until_reset = check_rate_limit(user.id, db)
    if is_rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {minutes_until_reset} minute{'s' if minutes_until_reset != 1 else ''}"
        )

    # Verify TOTP code with 30-second tolerance window (valid_window=1)
    totp = pyotp.TOTP(user.totp_secret)
    is_valid = totp.verify(payload.code, valid_window=1)

    # Record the attempt
    record_totp_attempt(user.id, is_valid, db)

    if not is_valid:
        # Log failed 2FA verification event before raising exception
        log_auth_event("2fa_failure", user, request, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    # Log successful 2FA verification event
    log_auth_event("2fa_success", user, request, db)
    print(f"[Login] Successful login with 2FA: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")

    # Generate and return JWT token
    token = create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/2fa/disable")
def disable_2fa(payload: TOTPDisableRequest, db: Session = Depends(get_db)):
    """
    Disable TOTP 2FA for a user.
    Requires user/password authentication.
    Clears the TOTP secret and sets is_2fa_enabled to False.
    """
    # Verify user credentials
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Disable 2FA by clearing secret and flag
    user.is_2fa_enabled = False
    user.totp_secret = None
    db.add(user)
    db.commit()

    # Log the disable event
    print(f"[2FA] Disabled: user_id={user.id}, username={user.username}, timestamp={datetime.utcnow().isoformat()}")

    return {"message": "2FA has been disabled successfully"}


# ---------------- Password Reset Flow (Dev Tier) ----------------

@app.post("/password-reset/request")
def password_reset_request(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    # Generic response to prevent user enumeration
    generic_msg = {"message": "If the account exists, a reset link has been sent."}

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return generic_msg

    # Generate token valid for 15 minutes
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    db_token = PasswordResetToken(token=token, user_id=user.id, expires_at=expires_at, used=False)
    db.add(db_token)
    db.commit()

    # Dev Tier: print token to logs (simulate email)
    print(f"[DEV] Password reset token for {user.email}: {token} (expires {expires_at.isoformat()} UTC)")

    return generic_msg


@app.post("/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    prt = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == payload.token)
        .first()
    )
    if not prt or prt.used or prt.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == prt.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.password = hash_password(payload.new_password)
    prt.used = True
    db.add(user)
    db.add(prt)
    db.commit()

    # Log password reset event
    log_auth_event("password_reset", user, request, db)

    return {"message": "Password updated successfully"}


# ---------------- Support Tickets (Dev Tier) ----------------

def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        # Decode to get username (sub)
        from .auth import SECRET_KEY, ALGORITHM

        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get("sub")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.post("/support/ticket", response_model=TicketResponse)
def create_ticket(payload: TicketCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = Ticket(owner_id=user.id, title=payload.title, description=payload.description, status="open")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/support/tickets", response_model=list[TicketResponse])
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tickets = db.query(Ticket).filter(Ticket.owner_id == user.id).order_by(Ticket.created_at.desc()).all()
    return tickets


@app.get("/2fa/status", response_model=TOTPStatusResponse)
def get_2fa_status(user: User = Depends(get_current_user)):
    """
    Get the 2FA status for the authenticated user.
    Requires JWT authentication.
    Returns whether 2FA is enabled for the user.
    """
    return TOTPStatusResponse(is_2fa_enabled=user.is_2fa_enabled)
