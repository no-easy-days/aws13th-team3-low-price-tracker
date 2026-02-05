from datetime import datetime

from pydantic import BaseModel, EmailStr


## Auth
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

## User

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

## Token
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int