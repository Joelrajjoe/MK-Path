"""
YouTube Ingestion & Learning Intelligence Processor
Unifies metadata fetching, transcript segmentation, concept extraction, RAG embedding, and study note generation.
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .parser import extract_youtube_video_id
from .metadata import fetch_youtube_metadata
from .transcript import get_youtube_transcript
from .segmenter import TranscriptSegmenter
from .models import YouTubeIngestRequest, YouTubeProcessResult
from ... import crud
from ...models import Material, MaterialStatus, Concept, Relationship
from ..ai import AIService

logger = logging.getLogger("mkpath.youtube.processor")

class YouTubeProcessor:
    """
    Main processor transforming YouTube videos into first-class learning assets within MK-Path.
    """

    @classmethod
    async def ingest_video(
        cls,
        db: Any,
        clerk_user_id: str,
        request: YouTubeIngestRequest
    ) -> Dict[str, Any]:
        """
        Ingests a YouTube video, extracts captions, chunks with timestamps, and generates concepts.
        """
        video_id = extract_youtube_video_id(request.url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL format: '{request.url}'")

        # 1. Fetch metadata
        meta = await fetch_youtube_metadata(video_id, request.url)
        title = request.custom_title or meta.title

        # 2. Duplicate Detection (video_id + clerk_user_id)
        existing_materials = await crud.get_materials(db, clerk_user_id)
        for m in existing_materials:
            if m.get("source_type") == "youtube" and m.get("metadata", {}).get("video_id") == video_id:
                logger.info(f"Duplicate YouTube video detected for {video_id}. Returning existing material.")
                return {
                    "material_id": str(m["_id"]),
                    "video_id": video_id,
                    "title": m.get("title"),
                    "status": m.get("status"),
                    "is_duplicate": True
                }

        # 3. Retrieve Transcript
        transcript_res = await get_youtube_transcript(video_id, request.manual_transcript)
        full_text = transcript_res.get("text", "")
        raw_segments = transcript_res.get("raw_segments", [])

        if not transcript_res.get("success") and not full_text:
            # Create failed material entry so user can provide transcript manually
            failed_model = Material(
                clerk_user_id=clerk_user_id,
                title=title,
                file_name=f"YouTube - {title[:40]}",
                file_size=len(full_text.encode('utf-8')) if full_text else 1024,
                content_type="video/youtube",
                raw_text="",
                status=MaterialStatus.FAILED.value,
                source_type="youtube",
                mime_type="video/youtube",
                duration=meta.duration_seconds,
                error_message=transcript_res.get("error", "No transcript found.")
            )
            created_fail = await crud.create_material(db, failed_model)
            return {
                "material_id": str(created_fail["_id"]),
                "video_id": video_id,
                "title": title,
                "status": "FAILED",
                "error": transcript_res.get("error")
            }

        # 4. Segment transcript into semantic chunks
        semantic_chunks = TranscriptSegmenter.segment_transcript(raw_segments)

        # 5. Create Material Record in DB
        material_model = Material(
            clerk_user_id=clerk_user_id,
            title=title,
            file_name=f"YouTube: {title}",
            file_size=len(full_text.encode("utf-8")),
            content_type="video/youtube",
            raw_text=full_text,
            status=MaterialStatus.READY.value,
            source_type="youtube",
            mime_type="video/youtube",
            duration=meta.duration_seconds,
            transcription_status="completed",
            extraction_method="youtube_captions" if transcript_res.get("source") == "youtube_captions" else "user_provided",
            segments=semantic_chunks
        )

        material_record = await crud.create_material(db, material_model)
        material_id_str = str(material_record["_id"])

        # 6. RAG Chunking & Vector Embeddings
        chunk_records = []
        texts_to_embed = []
        for s_idx, chunk in enumerate(semantic_chunks):
            c_hash = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()
            chunk_id = f"{material_id_str}_yt_{s_idx}_{c_hash[:8]}"
            chunk_dict = {
                "chunk_id": chunk_id,
                "material_id": material_id_str,
                "clerk_user_id": clerk_user_id,
                "sequence": s_idx,
                "text": chunk["text"],
                "start_time": chunk["start"],
                "end_time": chunk["end"],
                "section": f"YouTube [{chunk['time_label']}]",
                "source_type": "youtube",
                "source_url": f"https://www.youtube.com/watch?v={video_id}&t={int(chunk['start'])}s",
                "content_hash": c_hash,
                "token_count": chunk["token_count"],
                "metadata": {
                    "video_id": video_id,
                    "channel": meta.channel,
                    "time_label": chunk["time_label"]
                }
            }
            chunk_records.append(chunk_dict)
            texts_to_embed.append(chunk["text"])

        if texts_to_embed:
            try:
                embeddings = await AIService.generate_embeddings(texts_to_embed)
                for c_dict, emb in zip(chunk_records, embeddings):
                    c_dict["embedding"] = emb
                    c_dict["embedding_model"] = "models/gemini-embedding-001"
                    c_dict["embedding_status"] = "completed" if any(emb) else "fallback"
            except Exception as e:
                logger.warning(f"Embedding generation failed for YouTube {video_id}: {e}")

        await crud.save_material_chunks(db, material_id_str, chunk_records)

        # 7. AI Concept & Prerequisite Extraction
        concepts_extracted = 0
        try:
            extraction = await AIService.extract_concepts_and_relationships(full_text[:12000])
            concepts = extraction.get("concepts", [])
            relationships = extraction.get("relationships", [])

            for c in concepts:
                concept_model = Concept(
                    clerk_user_id=clerk_user_id,
                    material_id=material_id_str,
                    name=c["name"],
                    description=c.get("description", ""),
                    difficulty=c.get("difficulty", "intermediate"),
                    prerequisites=c.get("prerequisites", []),
                    exam_relevance=c.get("exam_relevance", 80),
                    industry_relevance=c.get("industry_relevance", 85),
                    source_refs=[{"source": "youtube", "video_id": video_id, "title": title}]
                )
                await crud.create_concept(db, concept_model)
                concepts_extracted += 1

            for r in relationships:
                rel_model = Relationship(
                    clerk_user_id=clerk_user_id,
                    material_id=material_id_str,
                    source_concept_name=r["source"],
                    target_concept_name=r["target"],
                    relationship_type=r.get("relationship_type", "prerequisite_of")
                )
                await crud.create_relationship(db, rel_model)
        except Exception as e:
            logger.warning(f"Concept extraction from YouTube failed: {e}")

        return {
            "material_id": material_id_str,
            "video_id": video_id,
            "title": title,
            "channel": meta.channel,
            "duration_minutes": round(meta.duration_seconds / 60, 1),
            "concepts_extracted_count": concepts_extracted,
            "chunks_indexed_count": len(chunk_records),
            "status": "READY",
            "thumbnail_url": meta.thumbnail_url,
            "source_url": meta.source_url
        }
