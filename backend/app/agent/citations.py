"""
MK-Path 2.0 Citation and Source Attribution System
Formats and validates evidence from learner materials, internal state, and web sources.
"""
from typing import List, Dict, Any, Optional
from .models import SourceCitation, SourceCategory

class CitationBuilder:
    """
    Constructs verifiable, non-hallucinated citations for agent responses.
    """

    @staticmethod
    def from_material_chunk(chunk: Dict[str, Any], snippet_len: int = 140) -> SourceCitation:
        text = chunk.get("text", "")
        snip = text[:snippet_len] + "..." if len(text) > snippet_len else text
        return SourceCitation(
            source_type=SourceCategory.LEARNER_MATERIAL,
            title=chunk.get("section") or chunk.get("material_title") or "Study Material",
            reference_id=chunk.get("chunk_id") or str(chunk.get("_id", "")),
            snippet=snip,
            page=chunk.get("page"),
            confidence=chunk.get("score", 1.0)
        )

    @staticmethod
    def from_youtube_segment(segment: Dict[str, Any], snippet_len: int = 140) -> SourceCitation:
        text = segment.get("text", "")
        snip = text[:snippet_len] + "..." if len(text) > snippet_len else text
        start_secs = segment.get("start", 0.0)
        mins = int(start_secs // 60)
        secs = int(start_secs % 60)
        formatted_ts = f"{mins:02d}:{secs:02d}"

        return SourceCitation(
            source_type=SourceCategory.YOUTUBE_SOURCE,
            title=segment.get("video_title") or "YouTube Video Lecture",
            reference_id=segment.get("video_id"),
            snippet=snip,
            timestamp_seconds=start_secs,
            timestamp_formatted=formatted_ts,
            url=segment.get("url"),
            confidence=1.0
        )

    @staticmethod
    def from_learner_state(metric_name: str, value: Any, detail: str) -> SourceCitation:
        return SourceCitation(
            source_type=SourceCategory.INTERNAL_LEARNER_STATE,
            title=f"Learner State: {metric_name}",
            snippet=f"{metric_name} = {value}. {detail}",
            confidence=1.0
        )

    @staticmethod
    def from_web_source(title: str, url: str, snippet: str) -> SourceCitation:
        return SourceCitation(
            source_type=SourceCategory.WEB_CURRENT_SOURCE,
            title=title,
            snippet=snippet,
            url=url,
            confidence=0.9
        )
