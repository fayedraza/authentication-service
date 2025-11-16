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


class LoginStep1Response(BaseModel):
    requires2fa: bool
    message: Optional[str] = None


class TOTPVerifyRequest(BaseModel):
    username: str
    code: str


class EnrollRequest(BaseModel):
    username: str
    password: str


class EnrollResponse(BaseModel):
    otpauth_uri: str


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
