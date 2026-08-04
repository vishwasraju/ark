"""API routes for retrieving individual nodes."""
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from api.db import get_pool
from api.models import NodeResponse
from api.auth import verify_api_key

router = APIRouter(tags=["nodes"])

@router.get("/nodes/{slug:path}", response_model=NodeResponse, dependencies=[Depends(verify_api_key)])
async def get_node(slug: str):
    """Fetch a single node by its slug."""
    pool = await get_pool()
    query_sql = """
        SELECT 
            slug, type, title, description, tags, source_doc, source_pages, 
            topic, content, timestamp
        FROM okf_nodes
        WHERE slug = $1;
    """
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query_sql, slug)
        
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with slug '{slug}' not found"
        )
        
    return NodeResponse(
        slug=row["slug"],
        type=row["type"],
        title=row["title"],
        description=row["description"],
        tags=row["tags"] or [],
        source_doc=row["source_doc"],
        source_pages=row["source_pages"],
        topic=row["topic"],
        content=row["content"],
        timestamp=row["timestamp"]
    )
