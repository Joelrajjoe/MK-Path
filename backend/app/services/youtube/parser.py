"""
YouTube URL Parser & Video ID Extractor
"""
import re
from typing import Optional

def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extracts canonical YouTube 11-character video ID from diverse URL formats:
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://www.youtube.com/embed/dQw4w9WgXcQ
    - https://www.youtube.com/v/dQw4w9WgXcQ
    - https://m.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtube.com/shorts/dQw4w9WgXcQ
    """
    if not url:
        return None
        
    url = url.strip()
    
    # 1. Direct ID pattern
    if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None
