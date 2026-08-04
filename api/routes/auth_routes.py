"""Authentication routes for the OKF Knowledge Store API."""
from fastapi import APIRouter, HTTPException, status, Depends
from api.db import get_pool
from api.models import UserCreate, UserLogin, TokenResponse
from api.auth import hash_password, verify_password, create_jwt_token

router = APIRouter(tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(user: UserCreate):
    """Register a new user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if username exists
        existing_user = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1", user.username
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash password and insert user
        pwd_hash = hash_password(user.password)
        new_user_id = await conn.fetchval(
            "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id",
            user.username, pwd_hash
        )
        
        token = create_jwt_token(new_user_id, user.username)
        return TokenResponse(token=token, username=user.username, message="registered")

@router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    """Login and get a JWT token."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        db_user = await conn.fetchrow(
            "SELECT id, username, password_hash FROM users WHERE username = $1", user.username
        )
        
        if not db_user or not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
            
        token = create_jwt_token(db_user["id"], db_user["username"])
        return TokenResponse(token=token, username=db_user["username"], message="success")
