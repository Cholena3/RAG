import secrets
import pyotp
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.database import get_db
from app.models.user import User, UserSession, AuditLog
from app.models.api_key import APIKey
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    TokenRefresh, APIKeyCreate, APIKeyResponse, APIKeyCreated,
    PasswordResetRequest, PasswordResetConfirm, UserUpdate,
    ChangePassword, Enable2FAResponse, Verify2FA, SessionResponse,
    AuditLogResponse, DeleteAccountRequest,
)
from app.middleware.auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)
from app.config import get_settings

_settings = get_settings()

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


async def log_audit(db: AsyncSession, user_id, action: str, request: Request = None,
                    resource_type: str = None, resource_id: str = None, details: str = None):
    """Create an audit log entry."""
    ip = request.client.host if request and request.client else None
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
    )
    db.add(log)


async def create_session(db: AsyncSession, user: User, request: Request, refresh_token: str):
    """Create a new session record."""
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    device_info = request.headers.get("User-Agent", "Unknown")[:500] if request else None
    ip_address = request.client.host if request and request.client else None
    expires_at = datetime.now(timezone.utc) + timedelta(days=_settings.refresh_token_expire_days)
    
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session)
    return session


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # Send verification email (generate token)
    token = secrets.token_urlsafe(32)
    r = aioredis.from_url(_settings.redis_url, decode_responses=True)
    await r.setex(f"email_verify:{token}", 86400, str(user.id))  # 24 hours
    await r.aclose()
    
    # In production, send email with verification link
    import structlog
    structlog.get_logger().info("email_verification_token", token=token, user_id=str(user.id))
    
    await log_audit(db, user.id, "user.registered", request)
    return user


@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify email using token sent during registration."""
    r = aioredis.from_url(_settings.redis_url, decode_responses=True)
    user_id = await r.get(f"email_verify:{token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    user.email_verified = True
    await r.delete(f"email_verify:{token}")
    await r.aclose()
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    # Check 2FA if enabled
    if user.totp_secret:
        if not data.totp_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                requires_2fa=True,
            )
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(data.totp_code):
            await log_audit(db, user.id, "login.2fa_failed", request)
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    await create_session(db, user, request, refresh_token)
    await log_audit(db, user.id, "user.login", request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, request: Request, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Verify session exists
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    session_result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.is_active == True
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or revoked")
    
    # Update session last used
    session.last_used_at = datetime.now(timezone.utc)
    
    new_access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))
    
    # Update session with new token hash
    session.token_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        has_2fa=user.totp_secret is not None,
        created_at=user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(data: UserUpdate, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Update user profile (name, avatar)."""
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    
    await log_audit(db, user.id, "user.profile_updated", request)
    await db.flush()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        has_2fa=user.totp_secret is not None,
        created_at=user.created_at,
    )


@router.post("/change-password")
async def change_password(data: ChangePassword, request: Request, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    """Change password for authenticated user."""
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    user.hashed_password = hash_password(data.new_password)
    await log_audit(db, user.id, "user.password_changed", request)
    return {"message": "Password changed successfully"}


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(user: User = Depends(get_current_user)):
    """Generate 2FA secret and QR code URI."""
    if user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=user.email, issuer_name=_settings.app_name)
    
    return Enable2FAResponse(secret=secret, qr_uri=qr_uri)


@router.post("/2fa/verify")
async def verify_2fa(data: Verify2FA, request: Request, secret: str, user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    """Verify and enable 2FA with the provided code."""
    totp = pyotp.TOTP(secret)
    if not totp.verify(data.totp_code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user.totp_secret = secret
    await log_audit(db, user.id, "user.2fa_enabled", request)
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(data: Verify2FA, request: Request, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Disable 2FA (requires current TOTP code)."""
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(data.totp_code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user.totp_secret = None
    await log_audit(db, user.id, "user.2fa_disabled", request)
    return {"message": "2FA disabled successfully"}


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(request: Request, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """List all active sessions for the current user."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc)
        ).order_by(UserSession.last_used_at.desc())
    )
    sessions = result.scalars().all()
    
    # Get current session token hash from request (if available)
    current_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    return [
        SessionResponse(
            id=s.id,
            device_info=s.device_info,
            ip_address=s.ip_address,
            is_current=False,  # Can't determine from access token
            created_at=s.created_at,
            last_used_at=s.last_used_at,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Revoke a specific session."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    await log_audit(db, user.id, "user.session_revoked", request, "session", session_id)
    return {"message": "Session revoked"}


@router.delete("/sessions")
async def revoke_all_sessions(request: Request, user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    """Revoke all sessions except current."""
    await db.execute(
        delete(UserSession).where(UserSession.user_id == user.id)
    )
    await log_audit(db, user.id, "user.all_sessions_revoked", request)
    return {"message": "All sessions revoked"}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(skip: int = 0, limit: int = 50, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Get audit logs for the current user."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )
    return result.scalars().all()


@router.delete("/account")
async def delete_account(data: DeleteAccountRequest, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Permanently delete user account and all associated data."""
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    # Log before deletion
    import structlog
    structlog.get_logger().info("account_deleted", user_id=str(user.id), email=user.email)
    
    # Delete user (cascades to documents, conversations, api_keys, sessions, audit_logs)
    await db.delete(user)
    
    return {"message": "Account deleted successfully"}


@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(data: APIKeyCreate, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    raw_key = f"dm_{secrets.token_urlsafe(32)}"
    api_key = APIKey(
        owner_id=user.id,
        name=data.name,
        key_hash=hash_password(raw_key),
        prefix=raw_key[:8],
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    await log_audit(db, user.id, "api_key.created", request, "api_key", str(api_key.id))
    return APIKeyCreated(**APIKeyResponse.model_validate(api_key).model_dump(), key=raw_key)


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.owner_id == user.id))
    return result.scalars().all()


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, request: Request, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Delete an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.owner_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    await db.delete(api_key)
    await log_audit(db, user.id, "api_key.deleted", request, "api_key", key_id)
    return {"message": "API key deleted"}


@router.post("/password-reset/request")
async def request_password_reset(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Generate a password reset token (stored in Redis, valid 15 min)."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    # Always return success to avoid email enumeration
    if user:
        token = secrets.token_urlsafe(32)
        r = aioredis.from_url(_settings.redis_url, decode_responses=True)
        await r.setex(f"pw_reset:{token}", 900, str(user.id))
        await r.aclose()
        # In production, send this token via email
        # For dev, log it
        import structlog
        structlog.get_logger().info("password_reset_token", token=token, user_id=str(user.id))
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(data: PasswordResetConfirm, request: Request, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid token."""
    r = aioredis.from_url(_settings.redis_url, decode_responses=True)
    user_id = await r.get(f"pw_reset:{data.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.hashed_password = hash_password(data.new_password)
    await r.delete(f"pw_reset:{data.token}")
    await r.aclose()
    await log_audit(db, user.id, "user.password_reset", request)
    return {"message": "Password has been reset successfully."}
