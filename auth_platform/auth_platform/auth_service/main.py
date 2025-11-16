from fastapi import FastAPI, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from .db import get_db, init_db
from .models import User, PasswordResetToken, Ticket
from .schemas import (
    UserCreate,
    UserLogin,
    Token,
    LoginStep1Response,
    EnrollRequest,
    EnrollResponse,
    TOTPVerifyRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    TicketCreate,
    TicketResponse,
)
from .auth import hash_password, verify_password, create_access_token
from fastapi.middleware.cors import CORSMiddleware
from typing import Union
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

@app.on_event("startup")
def startup():
    init_db()

@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email or username already exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if user.tier not in ("dev", "pro"):
        raise HTTPException(status_code=400, detail="Tier must be 'dev' or 'pro'")

    hashed_pw = hash_password(user.password)
    new_user = User(
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password=hashed_pw,
        tier=user.tier
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.username)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=Union[Token, LoginStep1Response])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # If 2FA is enabled, require TOTP verification in a second step
    if user.is_2fa_enabled:
        return LoginStep1Response(requires2fa=True, message="TOTP required")

    token = create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/2fa/enroll", response_model=EnrollResponse)
def enroll_2fa(payload: EnrollRequest, db: Session = Depends(get_db)):
    """
    Simple protection for dev tier: require user/password to enroll.
    In production, you would typically protect this with an authenticated session/JWT.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Generate or reuse a TOTP secret and mark 2FA enabled
    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
    user.is_2fa_enabled = True
    db.add(user)
    db.commit()
    db.refresh(user)

    issuer = os.getenv("AUTH_SERVICE_ISSUER", "AuthService")
    totp = pyotp.TOTP(user.totp_secret)
    otpauth_uri = totp.provisioning_uri(name=user.username, issuer_name=issuer)
    return EnrollResponse(otpauth_uri=otpauth_uri)


@app.post("/2fa/verify", response_model=Token)
def verify_totp(payload: TOTPVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.is_2fa_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled for user")

    totp = pyotp.TOTP(user.totp_secret)
    is_valid = totp.verify(payload.code, valid_window=1)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    token = create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


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
def password_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
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

    return {"message": "Password updated successfully"}


# ---------------- Support Tickets (Dev Tier) ----------------

def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        # Decode to get username (sub)
        from .auth import SECRET_KEY, ALGORITHM

        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

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
