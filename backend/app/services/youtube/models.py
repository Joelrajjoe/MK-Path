"""
YouTube Ingestion Schemas & Models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class YouTubeSegment(BaseModel):
    segment_id: str
    text: str
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    duration: float = Field(..., description="Duration in seconds")
    topic_label: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)

class YouTubeMetadata(BaseModel):
    video_id: str
    title: str
    channel: str
    duration_seconds: float
    description: str
    thumbnail_url: str
    publish_date: Optional[str] = None
    view_count: Optional[int] = None
    source_url: str

class YouTubeIngestRequest(BaseModel):
    url: str
    manual_transcript: Optional[str] = None
    custom_title: Optional[str] = None

class YouTubeProcessResult(BaseModel):
    material_id: str
    video_id: str
    title: str
    channel: str
    duration_minutes: float
    concepts_extracted_count: int
    chunks_indexed_count: int
    structured_notes: Optional[Dict[str, Any]] = None
    status: str = "READY"
    created_at: datetime = Field(default_factory=datetime.utcnow)
