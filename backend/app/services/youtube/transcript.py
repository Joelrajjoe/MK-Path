"""
YouTube Transcript & Caption Retrieval Engine
Fetches authorized captions with multi-language fallback and timestamp normalization.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger("mkpath.youtube.transcript")

async def get_youtube_transcript(
    video_id: str,
    manual_transcript: Optional[str] = None
) -> Dict[str, Any]:
    """
    Acquires compliant transcript from:
    1. Direct user-supplied transcript
    2. youtube_transcript_api if available
    3. Structural caption fallback
    """
    # 1. User supplied transcript
    if manual_transcript and manual_transcript.strip():
        raw_text = manual_transcript.strip()
        segments = [{
            "text": raw_text,
            "start": 0.0,
            "duration": 600.0
        }]
        return {
            "source": "user_provided",
            "text": raw_text,
            "raw_segments": segments,
            "success": True
        }

    # 2. Automated Caption Retrieval via youtube_transcript_api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Async wrap of blocking call
        def _fetch():
            try:
                # Try English first, then list all transcripts
                return YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
            except Exception:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Find any generated or manual transcript
                for t in transcript_list:
                    return t.fetch()
                raise Exception("No transcript tracks found.")

        fetched_segments = await asyncio.to_thread(_fetch)
        
        if fetched_segments:
            full_text = " ".join([seg.get("text", "") for seg in fetched_segments])
            return {
                "source": "youtube_captions",
                "text": full_text,
                "raw_segments": fetched_segments,
                "success": True
            }
    except Exception as e:
        logger.info(f"youtube_transcript_api not available or captions disabled for {video_id}: {e}")

    # 3. Transparent Failure (Do not fabricate transcript)
    return {
        "source": "unavailable",
        "text": "",
        "raw_segments": [],
        "success": False,
        "error": "No automated captions found for this video. You can paste the transcript or notes manually."
    }
