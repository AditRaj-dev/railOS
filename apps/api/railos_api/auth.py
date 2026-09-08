"""Authentication and authorization services for RailOS.

Implements Argon2id password hashing, 15-minute access JWTs, rotating 30-day
refresh tokens, admin account lifecycle, and backward-compatible synthetic header
fallback for local demos and development.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from railos_model import UserRole
from .roles import normalize_role

# Config
JWT_SECRET = os.getenv("RAILOS_JWT_SECRET", "railos-insecure-dev-jwt-secret-key-32-chars-min")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
ENABLE_SYNTHETIC_AUTH = os.getenv("ENABLE_SYNTHETIC_AUTH", "true").lower() == "true"

_ph = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)


def camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


class AuthDTO(BaseModel):
    model_config = ConfigDict(alias_generator=camel, populate_by_name=True, extra="forbid")


class TokenResponse(AuthDTO):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user_id: str
    role: str
    employee_id: str
    name: str


class LoginRequest(AuthDTO):
    employee_id: str
    password: str


class RefreshRequest(AuthDTO):
    refresh_token: str


class CreateSupervisorRequest(AuthDTO):
    employee_id: str
    name: str
    password: str
    email: str | None = None
    phone: str | None = None
    role: UserRole = UserRole.SUPERVISOR
    assigned_section_codes: list[str] = Field(default_factory=list)


class UpdateSupervisorAreasRequest(AuthDTO):
    field_area_ids: list[str] = Field(default_factory=list)
    section_codes: list[str] = Field(default_factory=list)


class ResetPasswordRequest(AuthDTO):
    new_password: str


class UserAccount(AuthDTO):
    user_id: str
    employee_id: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    active: bool = True
    created_at_iso: str = ""
    assigned_sections: list[str] = Field(default_factory=list)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _ph.hash(password)


def verify_password(hash_str: str, password: str) -> bool:
    """Verify a plain password against an Argon2id hash."""
    try:
        return _ph.verify(hash_str, password)
    except (VerifyMismatchError, Exception):
        return False


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of refresh token for database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: str,
    role: str,
    employee_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create 15-minute access JWT."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "role": role,
        "emp": employee_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
        "iss": "railos-auth",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token() -> tuple[str, str, datetime]:
    """Generate secure random 30-day refresh token and return (raw, hashed, expires_at)."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], issuer="railos-auth")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired"},
        )
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_INVALID", "message": f"Invalid access token: {err}"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_header: str | None = Header(None, alias="X-RailOS-User"),
    role_header: str | None = Header(None, alias="X-RailOS-Role"),
) -> UserAccount:
    """Extract authenticated user from JWT Bearer or fallback synthetic headers."""
    # 1. Preferred production path: JWT Bearer token
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        role = normalize_role(payload.get("role", "SUPERVISOR"))
        emp = payload.get("emp", user_id)
        if not user_id:
            raise HTTPException(401, {"code": "TOKEN_INVALID", "message": "Missing subject"})
        return UserAccount(
            userId=user_id,
            employeeId=emp,
            name=f"User {emp}",
            role=role,
            active=True,
        )

    # 2. Synthetic header fallback (only permitted when ENABLE_SYNTHETIC_AUTH is True)
    if ENABLE_SYNTHETIC_AUTH and user_header:
        role = normalize_role(role_header or "SUPERVISOR")
        return UserAccount(
            userId=user_header,
            employeeId=user_header,
            name=f"Synthetic {user_header}",
            role=role,
            active=True,
        )

    raise HTTPException(
        status_code=401,
        detail={"code": "UNAUTHENTICATED", "message": "Missing Authorization header or Bearer token"},
    )


def require_role(*allowed_roles: str):
    """FastAPI dependency to enforce specific roles (ADMIN always allowed)."""
    norm_allowed = {normalize_role(r) for r in allowed_roles}
    def check_role(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        user_role_norm = normalize_role(user.role)
        if user_role_norm != "ADMIN" and user_role_norm not in norm_allowed:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": f"Role '{user.role}' is not authorized for this resource"},
            )
        return user
    return check_role
