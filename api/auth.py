"""Authentication module for API access."""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

API_KEY = os.getenv("API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "okf-jwt-secret-change-me")
JWT_ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security_bearer = HTTPBearer(auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify the API key from the X-API-Key header.
    If API_KEY is not set in the environment, allows all requests (local dev).
    """
    if API_KEY:
        if api_key != API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key"
            )
    return api_key

def verify_mcp_api_key(request: Request):
    """
    Verify API key for MCP SSE clients, falling back to query parameters
    since SSE clients may not support custom headers.
    """
    if API_KEY:
        key = request.headers.get("X-API-Key")
        if not key:
            key = request.query_params.get("api_key")
        if key != API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key"
            )

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    pwd_bytes = password.encode('utf-8')
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(password: str, hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    pwd_bytes = password.encode('utf-8')
    hash_bytes = hash.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)

def create_jwt_token(user_id: int, username: str) -> str:
    """Create a JWT token valid for 24 hours."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": username,
        "user_id": user_id,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials = Security(security_bearer)
) -> dict:
    """
    Dependency to get the current user from JWT token.
    Extracts token from Authorization header or 'token' cookie.
    """
    token = None
    if bearer:
        token = bearer.credentials
    else:
        token = request.cookies.get("token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    return verify_jwt_token(token)
