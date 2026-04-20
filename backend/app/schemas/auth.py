from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime
import re


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None  # For 2FA


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    email_verified: bool
    has_2fa: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False


class TokenRefresh(BaseModel):
    refresh_token: str


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    class Config:
        from_attributes = True


class APIKeyCreated(APIKeyResponse):
    key: str  # only returned on creation


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class Enable2FAResponse(BaseModel):
    secret: str
    qr_uri: str


class Verify2FA(BaseModel):
    totp_code: str


class SessionResponse(BaseModel):
    id: UUID
    device_info: str | None
    ip_address: str | None
    is_current: bool = False
    created_at: datetime
    last_used_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: str | None
    details: str | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str  # Must be "DELETE"

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, v: str) -> str:
        if v != "DELETE":
            raise ValueError("You must type DELETE to confirm account deletion")
        return v
