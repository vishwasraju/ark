"""API routes for searching nodes."""
from fastapi import APIRouter, Depends, Query, HTTPException, status
import asyncpg
from typing import List

from api.db import get_pool
from api.models import SearchResponse, SearchResult
from api.auth import verify_api_key

router = APIRouter(tags=["search"])

@router.get("/search", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def search_nodes(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Max number of results")
):
    """Search OKF nodes using PostgreSQL full-text search."""
    if not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )
    
    pool = await get_pool()
    query_sql = """
        SELECT 
            slug, type, title, description, tags, source_doc, source_pages, 
            topic, content, timestamp,
            ts_rank(search_vec, websearch_to_tsquery('english', $1)) as rank
        FROM okf_nodes
        WHERE search_vec @@ websearch_to_tsquery('english', $1)
        ORDER BY rank DESC
        LIMIT $2;
    """
    
    count_sql = """
        SELECT count(*)
        FROM okf_nodes
        WHERE search_vec @@ websearch_to_tsquery('english', $1);
    """
    
    async with pool.acquire() as conn:
        results = await conn.fetch(query_sql, q, limit)
        total_row = await conn.fetchrow(count_sql, q)
    
    search_results = []
    for row in results:
        search_results.append(SearchResult(
            slug=row["slug"],
            type=row["type"],
            title=row["title"],
            description=row["description"],
            tags=row["tags"] or [],
            source_doc=row["source_doc"],
            source_pages=row["source_pages"],
            topic=row["topic"],
            content=row["content"],
            timestamp=row["timestamp"],
            rank=row["rank"]
        ))
        
    return SearchResponse(
        results=search_results,
        total=total_row["count"],
        query=q
    )
