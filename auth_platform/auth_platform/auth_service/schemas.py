from pydantic import BaseModel

from typing import Literal, Optional

class UserCreate(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: str
    password: str
    tier: Literal["dev", "pro"]

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegistrationResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    otpauth_uri: str
    requires_2fa_setup: bool = True


class LoginStep1Response(BaseModel):
    requires2fa: bool
    message: Optional[str] = None
    username: Optional[str] = None


class TOTPVerifyRequest(BaseModel):
    username: str
    code: str


class EnrollRequest(BaseModel):
    username: str
    password: str


class EnrollResponse(BaseModel):
    otpauth_uri: str


class TOTPDisableRequest(BaseModel):
    username: str
    password: str


class TOTPStatusResponse(BaseModel):
    is_2fa_enabled: bool


# Password reset
class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Tickets
class TicketCreate(BaseModel):
    title: str
    description: str


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str

    class Config:
        from_attributes = True
