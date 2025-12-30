from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List
import secrets
import hashlib
from datetime import datetime

from ..db import get_db
from ..models import User, ApiKey
from ..schemas import ApiKeyCreate, ApiKeyResponse
from ..auth import SECRET_KEY, ALGORITHM
import jwt

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"]
)

def get_current_user(
    db: Session = Depends(get_db),
    authorization: str = Header(..., alias="Authorization"),
):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get("sub")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def generate_api_key():
    """Generate a random API key and its hash."""
    # Prefix "sk_" for secret key
    raw_key = "sk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    # Store only prefix for display
    key_prefix = raw_key[:7]
    return raw_key, key_hash, key_prefix

@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all active API keys for the current user."""
    keys = db.query(ApiKey).filter(
        ApiKey.user_id == user.id,
        ApiKey.status == "active"
    ).order_by(ApiKey.created_at.desc()).all()
    return keys

@router.post("", response_model=ApiKeyResponse)
def create_api_key(payload: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new API key."""
    # Check Tier Limits
    active_keys_count = db.query(ApiKey).filter(
        ApiKey.user_id == user.id,
        ApiKey.status == "active"
    ).count()

    # Limit Logic: Dev = 1, Pro = Unlimited
    if user.tier == "dev":
        if active_keys_count >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dev tier is limited to 1 active API key. Upgrade to Pro for unlimited keys."
            )
    # Pro tier has no limit

    raw_key, key_hash, key_prefix = generate_api_key()

    new_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=payload.label,
        status="active"
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    # Return key only once!
    response = ApiKeyResponse.from_orm(new_key)
    response.key = raw_key
    return response

@router.post("/{key_id}/rotate", response_model=ApiKeyResponse)
def rotate_api_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rotate an API key: Revoke old one, create new one with same label."""
    old_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user.id
    ).first()

    if not old_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if old_key.status != "active":
        raise HTTPException(status_code=400, detail="Cannot rotate an inactive key")

    # Revoke old key
    old_key.status = "revoked_rotated"
    db.add(old_key)

    # Create new key
    raw_key, key_hash, key_prefix = generate_api_key()

    new_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=old_key.label, # Keep same label
        status="active"
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    response = ApiKeyResponse.from_orm(new_key)
    response.key = raw_key
    return response

@router.delete("/{key_id}")
def revoke_api_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke an API key."""
    key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user.id
    ).first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.status = "revoked"
    db.add(key)
    db.commit()
    return {"message": "API key revoked successfully"}
