from pydantic import BaseModel

from typing import Literal

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
    token_type: str
