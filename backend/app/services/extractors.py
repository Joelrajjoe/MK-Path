import fitz  # PyMuPDF
import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from ..config import settings

logger = logging.getLogger("mkpath.extractors")

class AudioTranscriptionOutput(BaseModel):
    text: str = Field(description="The complete transcription text verbatim.")
    language: str = Field(description="The detected language code (e.g. en, es, fr).")
    segments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of segments, each containing text, start (float seconds), and end (float seconds) keys."
    )

async def transcribe_multimodal_gemini(file_bytes: bytes, mime_type: str, prompt: str) -> Dict[str, Any]:
    """Helper calling Gemini multimodal API to extract text/transcripts from audio, video, or images."""
    gemini_keys = settings.GEMINI_API_KEYS
    if not gemini_keys:
        raise Exception("Gemini API Keys are not configured in environment variables (.env).")
    
    # Try keys in cycle
    for idx, key in enumerate(gemini_keys):
        try:
            client = genai.Client(api_key=key)
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            # Clean JSON wrappers if present
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1] == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            
            data = json.loads(raw_text)
            validated = AudioTranscriptionOutput(**data)
            return validated.model_dump()
        except Exception as e:
            logger.error(f"Gemini transcription key {idx+1} failed: {e}")
            if idx == len(gemini_keys) - 1:
                raise e

async def perform_ocr_gemini(image_bytes: bytes, mime_type: str) -> str:
    """Helper using Gemini to perform OCR on a scanned page or image."""
    gemini_keys = settings.GEMINI_API_KEYS
    if not gemini_keys:
        raise Exception("Gemini API Keys are not configured in environment variables.")
        
    for idx, key in enumerate(gemini_keys):
        try:
            client = genai.Client(api_key=key)
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Read all text inside this image and transcribe it verbatim. Do not include headers, descriptions, or comments. Just return the extracted text."
                ]
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini OCR key {idx+1} failed: {e}")
            if idx == len(gemini_keys) - 1:
                raise e
def validate_text_quality(text: str) -> bool:
    if not text:
        return False
    if len(text.strip()) < 50:
        return False
    # Check printable character ratio
    printable = sum(1 for c in text if c.isprintable())
    if printable / len(text) < 0.7:
        return False
    # Check for excessive repetition (gibberish indicator)
    words = text.split()
    if len(words) > 20:
        unique_words = len(set(words))
        if unique_words / len(words) < 0.1:
            return False
    return True


class ContentExtractor:
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        raise NotImplementedError()


class PDFExtractor(ContentExtractor):
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = doc.page_count
            text = ""
            segments = []
            
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
                    segments.append({
                        "text": page_text.strip(),
                        "page": page_num + 1
                    })
            
            text = text.strip()
            
            # Detect image-only or scanned PDF
            if len(text) < 50 and page_count > 0:
                logger.info("PDF direct text extraction returned less than 50 chars. Triggering OCRExtractor...")
                ocr_extractor = OCRExtractor()
                ocr_result = await ocr_extractor.extract(file_bytes, mime_type)
                ocr_result["metadata"]["page_count"] = page_count
                return ocr_result
                
            doc.close()
            
            if not validate_text_quality(text):
                logger.warning("PDF extraction failed quality validation.")
                raise ValueError("EXTRACTION_QUALITY_LOW")
            
            return {
                "source_type": "pdf",
                "text": text,
                "segments": segments,
                "metadata": {
                    "page_count": page_count
                },
                "extraction_status": "processed",
                "ocr_status": "n/a",
                "transcription_status": "n/a",
                "extraction_method": "direct_text"
            }
        except Exception as e:
            logger.error(f"PDF direct text extraction failed: {e}")
            error_code = "EXTRACTION_QUALITY_LOW" if str(e) == "EXTRACTION_QUALITY_LOW" else "failed"
            return {
                "source_type": "pdf",
                "text": "",
                "segments": [],
                "metadata": {"page_count": 0},
                "extraction_status": "failed",
                "ocr_status": "n/a",
                "transcription_status": "n/a",
                "extraction_method": "direct_text",
                "error_code": error_code
            }


class TextExtractor(ContentExtractor):
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            text = file_bytes.decode("utf-8", errors="ignore").strip()
            if not validate_text_quality(text):
                raise ValueError("EXTRACTION_QUALITY_LOW")
            return {
                "source_type": "txt",
                "text": text,
                "segments": [{"text": text, "line_count": len(text.splitlines())}],
                "metadata": {},
                "extraction_status": "processed" if text else "failed",
                "ocr_status": "n/a",
                "transcription_status": "n/a",
                "extraction_method": "direct_text"
            }
        except Exception as e:
            logger.error(f"Text Extraction failed: {e}")
            error_code = "EXTRACTION_QUALITY_LOW" if str(e) == "EXTRACTION_QUALITY_LOW" else "failed"
            return {
                "source_type": "txt",
                "text": "",
                "segments": [],
                "metadata": {},
                "extraction_status": "failed",
                "ocr_status": "n/a",
                "transcription_status": "n/a",
                "extraction_method": "direct_text",
                "error_code": error_code
            }


class OCRExtractor(ContentExtractor):
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            # Check if it's a PDF
            if mime_type == "application/pdf":
                logger.info("Performing OCR on scanned PDF pages...")
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                full_text = ""
                segments = []
                
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    # Render page to PNG bytes
                    pix = page.get_pixmap()
                    png_bytes = pix.tobytes("png")
                    
                    page_text = await perform_ocr_gemini(png_bytes, "image/png")
                    if page_text:
                        full_text += page_text + "\n"
                        segments.append({
                            "text": page_text,
                            "page": page_num + 1
                        })
                doc.close()
                return {
                    "source_type": "pdf",
                    "text": full_text.strip(),
                    "segments": segments,
                    "metadata": {
                        "page_count": len(segments)
                    },
                    "extraction_status": "processed",
                    "ocr_status": "completed",
                    "transcription_status": "n/a",
                    "extraction_method": "ocr"
                }
            else:
                # Standard image (PNG, JPEG)
                logger.info(f"Performing OCR on image with mime_type {mime_type}...")
                text = await perform_ocr_gemini(file_bytes, mime_type)
                return {
                    "source_type": "image",
                    "text": text,
                    "segments": [{"text": text, "page": 1}],
                    "metadata": {},
                    "extraction_status": "processed" if text else "failed",
                    "ocr_status": "completed" if text else "failed",
                    "transcription_status": "n/a",
                    "extraction_method": "ocr"
                }
        except Exception as e:
            logger.error(f"OCR Extraction failed: {e}")
            return {
                "source_type": "image" if mime_type != "application/pdf" else "pdf",
                "text": "",
                "segments": [],
                "metadata": {},
                "extraction_status": "failed",
                "ocr_status": "failed",
                "transcription_status": "n/a",
                "extraction_method": "ocr"
            }


class AudioExtractor(ContentExtractor):
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            prompt = (
                "Transcribe this audio file verbatim. You MUST return a JSON object with the following keys: "
                "'text' (the full verbatim transcript string), 'language' (the language code like 'en'), "
                "and 'segments' (a list of objects, each containing a 'text' string, a 'start' float timestamp, "
                "and an 'end' float timestamp in seconds)."
            )
            result = await transcribe_multimodal_gemini(file_bytes, mime_type, prompt)
            
            text = result.get("text", "").strip()
            language = result.get("language", "en")
            segments = result.get("segments", [])
            
            duration = 0.0
            if segments:
                try:
                    duration = float(segments[-1].get("end", 0.0))
                except Exception:
                    pass
            
            return {
                "source_type": "audio",
                "text": text,
                "segments": segments,
                "metadata": {
                    "duration": duration,
                    "language": language
                },
                "extraction_status": "processed" if text else "failed",
                "ocr_status": "n/a",
                "transcription_status": "completed" if text else "failed",
                "extraction_method": "transcription"
            }
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {
                "source_type": "audio",
                "text": "",
                "segments": [],
                "metadata": {"duration": 0.0},
                "extraction_status": "failed",
                "ocr_status": "n/a",
                "transcription_status": "failed",
                "extraction_method": "transcription"
            }


class VideoExtractor(ContentExtractor):
    async def extract(self, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            prompt = (
                "Transcribe the audio track of this video file verbatim. You MUST return a JSON object with the following keys: "
                "'text' (the full verbatim transcript string), 'language' (the language code like 'en'), "
                "and 'segments' (a list of objects, each containing a 'text' string, a 'start' float timestamp, "
                "and an 'end' float timestamp in seconds)."
            )
            result = await transcribe_multimodal_gemini(file_bytes, mime_type, prompt)
            
            text = result.get("text", "").strip()
            language = result.get("language", "en")
            segments = result.get("segments", [])
            
            duration = 0.0
            if segments:
                try:
                    duration = float(segments[-1].get("end", 0.0))
                except Exception:
                    pass
                    
            return {
                "source_type": "video",
                "text": text,
                "segments": segments,
                "metadata": {
                    "duration": duration,
                    "language": language
                },
                "extraction_status": "processed" if text else "failed",
                "ocr_status": "n/a",
                "transcription_status": "completed" if text else "failed",
                "extraction_method": "transcription"
            }
        except Exception as e:
            logger.error(f"Video transcription failed: {e}")
            return {
                "source_type": "video",
                "text": "",
                "segments": [],
                "metadata": {"duration": 0.0},
                "extraction_status": "failed",
                "ocr_status": "n/a",
                "transcription_status": "failed",
                "extraction_method": "transcription"
            }
