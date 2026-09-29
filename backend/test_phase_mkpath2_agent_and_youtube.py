import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.agent.router import IntentRouter
from app.agent.models import AgentIntent, SourceCategory
from app.agent.citations import CitationBuilder
from app.services.youtube.parser import extract_youtube_video_id
from app.services.youtube.segmenter import TranscriptSegmenter

def test_intent_routing():
    print("Testing Intent Routing...")
    router = IntentRouter()
    
    test_cases = [
        ("Explain transformers and how self-attention works", AgentIntent.LEARNING_EXPLANATION),
        ("What skills do I need to become a Backend Engineer?", AgentIntent.CAREER_GUIDANCE),
        ("What are my current skill gaps in Python and databases?", AgentIntent.SKILL_GAP),
        ("What is new in LangGraph v0.2 and latest AI frameworks?", AgentIntent.CURRENT_INDUSTRY),
        ("What should I study today based on my mastery and deadlines?", AgentIntent.STUDY_PLANNING),
        ("Can you quiz me on binary search trees?", AgentIntent.CONCEPT_TUTOR),
        ("Help me prepare for an interview for a Senior Machine Learning role", AgentIntent.INTERVIEW_PREPARATION),
        ("Give me project ideas for distributed caching in Go", AgentIntent.PROJECT_GUIDANCE),
        ("Where can I find resources and tutorials for Kubernetes?", AgentIntent.RESOURCE_SEARCH),
        ("According to my uploaded document on page 4, what is the formula?", AgentIntent.DOCUMENT_QA),
        ("Hello, how can you help me today?", AgentIntent.GENERAL),
    ]
    
    for query, expected_intent in test_cases:
        routed = router.route(query)
        assert routed == expected_intent, f"Query '{query}' expected {expected_intent}, got {routed}"
        requirements = router.get_context_requirements(routed)
        assert isinstance(requirements, list)
        print(f"  [OK] '{query[:35]}...' -> {routed.value} (Needs {len(requirements)} context keys)")
    print("All Intent Routing tests passed!\n")

def test_youtube_parser():
    print("Testing YouTube Parser...")
    valid_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url, expected_id in valid_urls:
        vid = extract_youtube_video_id(url)
        assert vid == expected_id, f"URL {url} expected ID {expected_id}, got {vid}"
        print(f"  [OK] {url} -> {vid}")
        
    invalid_urls = [
        "https://example.com/watch?v=12345",
        "not_a_url",
        "https://youtube.com/watch?v=short",
    ]
    for url in invalid_urls:
        vid = extract_youtube_video_id(url)
        assert vid is None, f"URL {url} should have returned None, got {vid}"
        print(f"  [OK] Invalid URL correctly rejected: {url}")
    print("All YouTube Parser tests passed!\n")

def test_youtube_segmentation():
    print("Testing YouTube Segmenter...")
    raw_transcript = [
        {"start": 0.0, "duration": 4.0, "text": "Welcome to this tutorial on neural networks."},
        {"start": 4.0, "duration": 5.0, "text": "Today we will dive into backpropagation and gradient descent."},
        {"start": 9.0, "duration": 6.0, "text": "Let's first understand what a loss function represents."},
    ]
    segments = TranscriptSegmenter.segment_transcript(raw_transcript, target_word_count=10)
    assert len(segments) >= 1
    assert segments[0]["timestamp_start"] == "00:00"
    print(f"  [OK] Segmented {len(raw_transcript)} raw captions into {len(segments)} semantic segments.")
    print("All YouTube Segmenter tests passed!\n")

def test_citation_builder():
    print("Testing Citation Builder...")
    mat_cit = CitationBuilder.from_material_chunk({
        "material_title": "Deep Learning Notes",
        "page": 14,
        "section": "Attention Mechanisms",
        "text": "Self-attention computes dynamic weights..."
    })
    assert mat_cit.source_type == SourceCategory.LEARNER_MATERIAL
    assert mat_cit.title == "Attention Mechanisms"
    print(f"  [OK] Material citation formatted: {mat_cit.title} (Page {mat_cit.page})")

    yt_cit = CitationBuilder.from_youtube_segment({
        "video_title": "Attention Is All You Need Explained",
        "start": 255.0,
        "url": "https://youtu.be/dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ",
        "text": "The query and key matrices are multiplied..."
    })
    assert yt_cit.source_type == SourceCategory.YOUTUBE_SOURCE
    assert yt_cit.timestamp_formatted == "04:15"
    print(f"  [OK] YouTube citation formatted: {yt_cit.title} @ {yt_cit.timestamp_formatted}")
    print("All Citation Builder tests passed!\n")

if __name__ == "__main__":
    print("=== RUNNING MK-PATH 2.0 PHASE 1 & 2 TEST SUITE ===\n")
    test_intent_routing()
    test_youtube_parser()
    test_youtube_segmentation()
    test_citation_builder()
    print("=== ALL TESTS PASSED SUCCESSFULLY! ===")
