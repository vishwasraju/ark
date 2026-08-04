"""Admin routes for OKF Knowledge Store API."""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List
from api.db import get_pool
from api.models import TopicInfo, StatsResponse, NodeResponse
from api.auth import verify_api_key

router = APIRouter(tags=["admin"])

@router.get("/topics", response_model=List[TopicInfo], dependencies=[Depends(verify_api_key)])
async def get_topics():
    """Get list of unique topics with node count."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT topic, COUNT(*) as count 
            FROM okf_nodes 
            WHERE topic IS NOT NULL 
            GROUP BY topic 
            ORDER BY count DESC
        """)
        return [TopicInfo(topic=row["topic"], count=row["count"]) for row in rows]

@router.get("/stats", response_model=StatsResponse, dependencies=[Depends(verify_api_key)])
async def get_stats():
    """Get overall statistics for the knowledge store."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_nodes,
                COUNT(DISTINCT topic) as total_topics,
                MAX(timestamp) as latest_update
            FROM okf_nodes
        """)
        return StatsResponse(
            total_nodes=stats["total_nodes"] or 0,
            total_topics=stats["total_topics"] or 0,
            latest_update=stats["latest_update"]
        )

@router.delete("/nodes/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_node(slug: str):
    """Delete a node by its slug."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM okf_nodes WHERE slug = $1", slug)
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )

@router.get("/recent", response_model=List[NodeResponse], dependencies=[Depends(verify_api_key)])
async def get_recent(limit: int = Query(10, ge=1, le=100)):
    """Get the most recently added nodes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, slug, type, title, description, tags, source_doc, source_pages, topic, content, timestamp
            FROM okf_nodes
            ORDER BY timestamp DESC NULLS LAST
            LIMIT $1
        """, limit)
        return [NodeResponse(**dict(row)) for row in rows]
