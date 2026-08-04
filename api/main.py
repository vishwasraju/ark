"""Main entrypoint for OKF Knowledge Store API."""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

from api.db import get_pool, close_pool
from api.init_db import init_schema
from api.routes.search import router as search_router
from api.routes.nodes import router as nodes_router
from api.routes.auth_routes import router as auth_router
from api.routes.admin import router as admin_router
from api.mcp_server import mcp as mcp_server
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for FastAPI application."""
    # Startup
    pool = await get_pool()
    await init_schema(pool)
    yield
    # Shutdown
    await close_pool()


app = FastAPI(
    title="OKF Knowledge Store",
    description="REST API and MCP Server for OKF Markdown Files",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api")
app.include_router(nodes_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


# --- MCP SSE mount with optional API key auth ---

API_KEY = os.getenv("API_KEY")


class MCPAuthMiddleware:
    """ASGI middleware that checks API key for MCP SSE requests.

    Supports key via X-API-Key header or ?api_key= query param.
    """

    def __init__(self, asgi_app):
        self.app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and API_KEY:
            request = Request(scope, receive)
            key = request.headers.get("x-api-key") or request.query_params.get(
                "api_key"
            )
            if key != API_KEY:
                response = JSONResponse(
                    {"detail": "Invalid API Key"}, status_code=401
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


app.mount("/mcp", MCPAuthMiddleware(mcp_server.sse_app()))


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Serve dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))
