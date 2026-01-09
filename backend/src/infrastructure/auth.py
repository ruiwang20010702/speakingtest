"""
Authentication Module (JWT + RBAC)
Based on /fastapi-auth-patterns workflow.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from src.infrastructure.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/tokens")


# ============================================
# Models
# ============================================

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: int
    role: str


# ============================================
# Password Utilities
# ============================================

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================
# JWT Utilities
# ============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (must include 'sub' for user_id)
        expires_delta: Optional custom expiry time
    
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.
    
    Returns:
        TokenData if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        role = payload.get("role", "student")
        
        if user_id is None:
            return None
        
        return TokenData(user_id=int(user_id), role=role)
    except JWTError:
        return None


# ============================================
# Dependencies
# ============================================

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Dependency to extract current user ID from JWT token.
    
    Usage:
        @router.get("/me")
        async def get_me(user_id: int = Depends(get_current_user_id)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception
    
    return token_data.user_id


async def get_current_user_role(token: str = Depends(oauth2_scheme)) -> str:
    """Get current user's role from token."""
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data.role


# ============================================
# RBAC - Role-Based Access Control
# ============================================

def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user_id: int = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(token: str = Depends(oauth2_scheme)) -> int:
        token_data = decode_token(token)
        if token_data is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if token_data.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{token_data.role}' not authorized for this resource",
            )
        return token_data.user_id
    
    return role_checker


# Convenience decorators
require_teacher = require_role("teacher", "admin")
require_admin = require_role("admin")
require_student = require_role("student")
