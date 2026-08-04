"""MCP server implementation for OKF Knowledge Store (mcp SDK v2.0.0+)."""
import json
from mcp.server import MCPServer

from api.db import get_pool

# Create the MCP server instance
mcp = MCPServer("okf-knowledge-store")


@mcp.tool()
async def search_knowledge(query: str, limit: int = 5) -> str:
    """Search the OKF knowledge base by keyword.

    Returns matching documents with title, description, content, tags,
    and source information. Results are ranked by relevance.

    Args:
        query: The search query string.
        limit: Maximum number of results to return (default 5).
    """
    if not query.strip():
        return json.dumps({"error": "Query cannot be empty"})

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

    pool = await get_pool()
    async with pool.acquire() as conn:
        results = await conn.fetch(query_sql, query, limit)

    formatted_results = []
    for row in results:
        ts = row["timestamp"]
        formatted_results.append({
            "slug": row["slug"],
            "type": row["type"],
            "title": row["title"],
            "description": row["description"],
            "tags": row["tags"] or [],
            "source_doc": row["source_doc"],
            "source_pages": row["source_pages"],
            "topic": row["topic"],
            "content": row["content"],
            "timestamp": ts.isoformat() if ts else None,
            "rank": float(row["rank"]),
        })

    return json.dumps(formatted_results, indent=2)
