"""Database schema initialization."""
import asyncpg

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS okf_nodes (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    type TEXT,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT[],
    source_doc TEXT,
    source_pages TEXT,
    timestamp TIMESTAMPTZ,
    content TEXT NOT NULL,
    topic TEXT,
    search_vec TSVECTOR
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS okf_search_idx ON okf_nodes USING GIN(search_vec);

CREATE OR REPLACE FUNCTION okf_nodes_search_vec_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vec :=
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.content, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'okf_nodes_search_vec_update'
    ) THEN
        CREATE TRIGGER okf_nodes_search_vec_update
            BEFORE INSERT OR UPDATE ON okf_nodes
            FOR EACH ROW
            EXECUTE FUNCTION okf_nodes_search_vec_trigger();
    END IF;
END;
$$;
"""


async def init_schema(pool: asyncpg.Pool):
    """Initialize the database schema if it doesn't exist."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
