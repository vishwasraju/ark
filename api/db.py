"""Database connection pool module for OKF Knowledge Store."""
import os
import ssl
from urllib.parse import urlparse, unquote
import asyncpg
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None

def parse_db_url(url: str) -> dict:
    """Safely parse a postgresql:// URL into asyncpg connection keyword arguments."""
    parsed = urlparse(url)
    
    user = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/') if parsed.path else 'postgres'
    
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "database": database
    }

async def get_pool() -> asyncpg.Pool:
    """Get the database connection pool. Creates it if it doesn't exist."""
    global _pool
    if _pool is None:
        if not DATABASE_URL or "db:5432" in DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is missing or invalid. "
                "Please set DATABASE_URL to your Supabase / Cloud PostgreSQL connection string in your Cloud Host Environment Variables."
            )

        # Create unverified SSL context for cloud PostgreSQL services (Supabase pooler, Neon, etc.)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            # First try parsing explicit connection parameters for maximum robustness
            params = parse_db_url(DATABASE_URL)
            _pool = await asyncpg.create_pool(
                user=params["user"],
                password=params["password"],
                host=params["host"],
                port=params["port"],
                database=params["database"],
                ssl=ctx,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        except Exception:
            # Fallback to direct DSN string connection
            _pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                ssl=ctx,
                min_size=1,
                max_size=10,
                command_timeout=60
            )

    return _pool

async def close_pool():
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
