"""Pydantic models for API responses."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NodeResponse(BaseModel):
    """Model representing an OKF node in the store."""
    slug: str
    type: Optional[str] = None
    title: str
    description: Optional[str] = None
    tags: List[str] = []
    source_doc: Optional[str] = None
    source_pages: Optional[str] = None
    topic: Optional[str] = None
    content: str
    timestamp: Optional[datetime] = None

class SearchResult(NodeResponse):
    """Model for a search result, including the search rank."""
    rank: float

class SearchResponse(BaseModel):
    """Model for search response containing multiple results."""
    results: List[SearchResult]
    total: int
    query: str

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str
    username: str
    message: str = "success"

class TopicInfo(BaseModel):
    topic: str
    count: int

class StatsResponse(BaseModel):
    total_nodes: int
    total_topics: int
    latest_update: Optional[datetime] = None
