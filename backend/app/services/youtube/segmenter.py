"""
YouTube Transcript Segmenter
Normalizes timestamps, sentences, and builds semantic chunks (~200-400 words) with timestamp bounds.
"""
import hashlib
from typing import List, Dict, Any
from .models import YouTubeSegment

class TranscriptSegmenter:
    """
    Groups granular timed words into coherent pedagogical chunks preserving timestamp ranges.
    """

    @classmethod
    def segment_transcript(
        cls,
        raw_segments: List[Dict[str, Any]],
        target_word_count: int = 250
    ) -> List[Dict[str, Any]]:
        """
        Groups raw caption lines into semantic segments with start and end timestamps.
        """
        if not raw_segments:
            return []

        chunks = []
        current_words = []
        current_start = raw_segments[0].get("start", 0.0)
        current_end = current_start

        for seg in raw_segments:
            text = seg.get("text", "").strip()
            start = seg.get("start", 0.0)
            dur = seg.get("duration", 0.0)
            current_end = start + dur

            words = text.split()
            current_words.extend(words)

            if len(current_words) >= target_word_count:
                seg_text = " ".join(current_words)
                mins_start = int(current_start // 60)
                secs_start = int(current_start % 60)
                mins_end = int(current_end // 60)
                secs_end = int(current_end % 60)

                chunks.append({
                    "text": seg_text,
                    "start": round(current_start, 2),
                    "end": round(current_end, 2),
                    "timestamp_start": f"{mins_start:02d}:{secs_start:02d}",
                    "timestamp_end": f"{mins_end:02d}:{secs_end:02d}",
                    "duration": round(current_end - current_start, 2),
                    "time_label": f"{mins_start:02d}:{secs_start:02d} - {mins_end:02d}:{secs_end:02d}",
                    "token_count": len(current_words)
                })
                current_words = []
                current_start = current_end

        # Append trailing words
        if current_words:
            seg_text = " ".join(current_words)
            mins_start = int(current_start // 60)
            secs_start = int(current_start % 60)
            mins_end = int(current_end // 60)
            secs_end = int(current_end % 60)

            chunks.append({
                "text": seg_text,
                "start": round(current_start, 2),
                "end": round(current_end, 2),
                "timestamp_start": f"{mins_start:02d}:{secs_start:02d}",
                "timestamp_end": f"{mins_end:02d}:{secs_end:02d}",
                "duration": round(current_end - current_start, 2),
                "time_label": f"{mins_start:02d}:{secs_start:02d} - {mins_end:02d}:{secs_end:02d}",
                "token_count": len(current_words)
            })

        return chunks
