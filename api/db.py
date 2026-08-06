"""Database connection pool module for OKF Knowledge Store."""
import os
import ssl
import re
from urllib.parse import unquote
import asyncpg
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None

def parse_db_url(url: str) -> dict:
    """Robustly parse a postgresql:// URL into connection parameters."""
    if not url:
        raise ValueError("DATABASE_URL is empty")

    url = url.strip()

    # Match: postgresql://[user]:[password]@[host]:[port]/[database]
    # Also handles colons or special chars in password or misplaced @
    pattern = r'^(?:postgres(?:ql)?://)?(?:([^:@]+)(?::([^@]*))?@)?([^:/]+)(?::(\d+))?/(.+)$'
    match = re.match(pattern, url)

    if match:
        user, password, host, port, database = match.groups()
        # Clean up database name (remove query parameters if any)
        db_name = database.split('?')[0] if database else 'postgres'
        return {
            "user": unquote(user) if user else "postgres",
            "password": unquote(password) if password else "",
            "host": host,
            "port": int(port) if port else 5432,
            "database": db_name
        }

    # If regex fails, fallback to default parameters
    return {
        "user": "postgres",
        "password": "",
        "host": "localhost",
        "port": 5432,
        "database": "postgres"
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

        params = parse_db_url(DATABASE_URL)
        
        try:
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
