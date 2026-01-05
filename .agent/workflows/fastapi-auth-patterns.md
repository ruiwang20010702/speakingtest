---
description: Implement JWT authentication, OAuth2, and password hashing patterns for FastAPI applications.
---

# FastAPI Auth Patterns

Implement secure authentication and authorization for FastAPI applications using JWT tokens, OAuth2, and password hashing best practices.

## When to Use This Skill

- Implementing user login/logout flows
- Securing API endpoints with JWT tokens
- Managing user sessions and token refresh
- Implementing role-based access control (RBAC)
- Hashing and verifying passwords securely

## Core Concepts

### 1. Password Hashing

**NEVER store plain text passwords.** Use bcrypt or argon2.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

### 2. JWT Tokens

**Structure**: Header.Payload.Signature

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError

SECRET_KEY = "your-secret-key"  # Load from env in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

## Authentication Patterns

### Pattern 1: OAuth2 Password Bearer (Login Endpoint)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/tokens")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: int
    role: str

@router.post("/tokens", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login.
    Returns JWT access token.
    """
    # 1. Find user by email
    user = await user_repository.find_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # 3. Create token
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    
    return Token(access_token=access_token)
```

### Pattern 2: Current User Dependency

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/tokens")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = await user_repository.find_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    
    return user
```

### Pattern 3: Role-Based Access Control (RBAC)

```python
from functools import wraps
from fastapi import Depends, HTTPException, status

def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized for this resource",
            )
        return user
    return role_checker

# Usage examples
require_teacher = require_role("teacher", "admin")
require_admin = require_role("admin")
```

### Pattern 4: Token Refresh

```python
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token(user_id: int) -> str:
    """Create a longer-lived refresh token."""
    return create_access_token(
        data={"sub": str(user_id), "type": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Exchange refresh token for new access token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id = payload.get("sub")
    new_access_token = create_access_token(data={"sub": user_id})
    
    return Token(access_token=new_access_token)
```

## Security Best Practices

1. **Secret Key**: Use a strong, random secret (256+ bits). Load from env.
2. **Token Expiry**: Keep access tokens short-lived (15-60 mins).
3. **HTTPS Only**: Always use HTTPS in production.
4. **Rate Limiting**: Limit login attempts to prevent brute force.
5. **Password Policy**: Enforce minimum length (8+), complexity.

## Checklist

- [ ] Passwords hashed with bcrypt/argon2?
- [ ] JWT secret loaded from environment?
- [ ] Token expiry set appropriately?
- [ ] RBAC enforced on sensitive endpoints?
- [ ] Login endpoint rate-limited?
