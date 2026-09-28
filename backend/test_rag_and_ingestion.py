import os
import sys
import asyncio
import hashlib
from datetime import datetime
import fitz  # PyMuPDF

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Material, MaterialChunk, MaterialStatus, Question
from app.services.extractors import PDFExtractor, TextExtractor, OCRExtractor, validate_text_quality
from app.services.ai import AIService, LocalFallbackProvider
from app.database import DatabaseManager
import app.crud as crud

async def create_sample_pdf(text: str, is_empty: bool = False, is_scanned_simulation: bool = False) -> bytes:
    """Helper to generate a PDF in-memory using PyMuPDF."""
    if is_empty:
        return b""
    doc = fitz.open()
    page = doc.new_page()
    if not is_scanned_simulation:
        page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

async def run_all_tests():
    print("==================================================================")
    print("MK-PATH PHASE 24: INGESTION AND RAG STABILIZATION TEST HARNESS")
    print("==================================================================")

    db = DatabaseManager() # Local / in-memory demo DB mode
    user_alice = "user_clerk_alice_123"
    user_bob = "user_clerk_bob_456"

    # -------------------------------------------------------------------------
    # TEST 1: Valid Multi-Page PDF Ingestion & Extraction
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Ingesting Valid Multi-Page PDF...")
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Machine Learning Fundamentals: Supervised learning algorithms learn mappings from inputs to outputs based on labeled training dataset examples.", fontsize=11)
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Neural Networks and Backpropagation: Deep neural networks optimize multi-layer weights through gradient descent and backpropagation.", fontsize=11)
    valid_pdf_bytes = doc.tobytes()
    doc.close()

    pdf_extractor = PDFExtractor()
    extract_res = await pdf_extractor.extract(valid_pdf_bytes, "application/pdf")
    assert extract_res["extraction_status"] == "processed", "Test 1 Failed: Status should be processed"
    assert extract_res["metadata"]["page_count"] == 2, "Test 1 Failed: Page count should be 2"
    assert len(extract_res["segments"]) == 2, "Test 1 Failed: Segments should contain 2 pages"
    print("  -> Passed! Valid 2-page PDF extracted successfully with correct segments.")

    # -------------------------------------------------------------------------
    # TEST 2: Scanned PDF / Image-Only PDF Detection
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Ingesting Scanned/Image PDF (< 50 chars direct text)...")
    scanned_pdf_bytes = await create_sample_pdf("", is_scanned_simulation=True)
    
    # Mock OCR call to ensure deterministic and fast unit testing
    import app.services.extractors as ext_mod
    original_ocr = ext_mod.perform_ocr_gemini
    async def mock_ocr(b, m):
        return "Scanned document text transcribed via OCR layer."
    ext_mod.perform_ocr_gemini = mock_ocr
    
    try:
        extract_scanned = await pdf_extractor.extract(scanned_pdf_bytes, "application/pdf")
        assert extract_scanned["extraction_method"] == "ocr", "Test 2 Failed: Should redirect to OCR"
        assert extract_scanned["extraction_status"] == "processed"
        assert "Scanned document text" in extract_scanned["text"]
        print(f"  -> Passed! Scanned PDF detected and routed to OCR (method='{extract_scanned.get('extraction_method')}').")
    finally:
        ext_mod.perform_ocr_gemini = original_ocr

    # -------------------------------------------------------------------------
    # TEST 3: Short Document Ingestion
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Ingesting Short Document...")
    short_text = "Linear Regression is a foundational statistical method for continuous modeling."
    txt_extractor = TextExtractor()
    short_res = await txt_extractor.extract(short_text.encode("utf-8"), "text/plain")
    assert short_res["extraction_status"] == "processed", "Test 3 Failed: Short valid text should be processed"
    assert short_res["text"] == short_text
    print("  -> Passed! Short educational document successfully processed.")

    # -------------------------------------------------------------------------
    # TEST 4: Empty Document (0 bytes / no text)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Ingesting Empty Document (0 bytes)...")
    empty_pdf_bytes = await create_sample_pdf("", is_empty=True)
    empty_res = await pdf_extractor.extract(empty_pdf_bytes, "application/pdf")
    assert empty_res["extraction_status"] == "failed"
    assert empty_res.get("error_code") == "EMPTY_DOCUMENT"
    print("  -> Passed! Empty document correctly rejected with error_code='EMPTY_DOCUMENT'.")

    # -------------------------------------------------------------------------
    # TEST 5: Corrupted Document Handling
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Ingesting Corrupted PDF Bytes...")
    corrupted_bytes = b"%PDF-1.4 corrupt random junk data \x00\xff\xfe not a valid pdf"
    corrupt_res = await pdf_extractor.extract(corrupted_bytes, "application/pdf")
    assert corrupt_res["extraction_status"] == "failed"
    assert corrupt_res.get("error_code") == "CORRUPTED_DOCUMENT"
    print("  -> Passed! Corrupted document caught safely with error_code='CORRUPTED_DOCUMENT'.")

    # -------------------------------------------------------------------------
    # TEST 6: Canonical Chunk Creation and Hashing
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Canonical Chunking & Hashing...")
    material_id_1 = "mat_abc_001"
    chunk_text_1 = "Supervised learning utilizes labeled datasets to train algorithms for classification and regression."
    c_hash_1 = hashlib.sha256(chunk_text_1.encode("utf-8")).hexdigest()
    chunk_1 = MaterialChunk(
        chunk_id=f"{material_id_1}_chunk_0_{c_hash_1[:8]}",
        material_id=material_id_1,
        clerk_user_id=user_alice,
        sequence=0,
        text=chunk_text_1,
        page=1,
        section="Segment 1",
        source_type="pdf",
        content_hash=c_hash_1,
        embedding_model="models/gemini-embedding-001",
        embedding=[0.1, 0.2, 0.3, 0.4] + [0.0] * 764, # Mock 768-dim vector
        embedding_status="completed"
    )
    assert chunk_1.content_hash == c_hash_1
    assert chunk_1.material_id == material_id_1
    assert chunk_1.clerk_user_id == user_alice
    
    # Save chunk in CRUD
    await crud.save_material_chunks(db, material_id_1, [chunk_1.model_dump()])
    saved_chunks = await crud.get_material_chunks(db, material_id_1)
    assert len(saved_chunks) == 1
    assert saved_chunks[0]["chunk_id"] == chunk_1.chunk_id
    print("  -> Passed! Canonical MaterialChunk created, hashed, and persisted.")

    # -------------------------------------------------------------------------
    # TEST 7: Cross-User Isolation (Wrong User / Security Boundary)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Cross-User Security Scoping...")
    # Query Alice's chunks as Bob
    query_emb = [0.1, 0.2, 0.3, 0.4] + [0.0] * 764
    bob_retrieval = await crud.TEMPORARY_VECTOR_SEARCH_FALLBACK(
        db, 
        clerk_user_id=user_bob, # Bob searching
        query_embedding=query_emb,
        top_k=5,
        min_similarity=0.1
    )
    assert len(bob_retrieval) == 0, "Test 7 Failed: Bob should NOT be able to retrieve Alice's chunks!"
    
    # Query as Alice
    alice_retrieval = await crud.TEMPORARY_VECTOR_SEARCH_FALLBACK(
        db,
        clerk_user_id=user_alice, # Alice searching
        query_embedding=query_emb,
        top_k=5,
        min_similarity=0.1
    )
    assert len(alice_retrieval) == 1, "Test 7 Failed: Alice should retrieve her own chunk"
    print("  -> Passed! Strict user isolation verified. Bob received 0 chunks from Alice's material.")

    # -------------------------------------------------------------------------
    # TEST 8: Retrieval with No Matching Context
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Vector Search with Orthogonal / No Matching Context...")
    orthogonal_emb = [-0.9, -0.9, -0.9, -0.9] + [0.0] * 764
    no_match_retrieval = await crud.TEMPORARY_VECTOR_SEARCH_FALLBACK(
        db,
        clerk_user_id=user_alice,
        query_embedding=orthogonal_emb,
        top_k=5,
        min_similarity=0.7 # High similarity threshold
    )
    assert len(no_match_retrieval) == 0, "Test 8 Failed: Orthogonal query should return empty results"
    print("  -> Passed! Vector search returned empty list when similarity is below threshold.")

    # -------------------------------------------------------------------------
    # TEST 9: Server-Side Source Reference Validation
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Enforcing Server-Side Source Reference Grounding...")
    retrieved_chunks = [chunk_1.model_dump()]
    
    # Case A: LLM generated questions with genuine retrieved chunk_id
    genuine_generated_questions = [
        {
            "question_text": "What is the primary function of supervised learning?",
            "options": ["Mapping inputs to outputs with labels", "Clustering unlabeled data", "Random exploration", "None"],
            "correct_option_index": 0,
            "source_refs": [{"chunk_id": chunk_1.chunk_id}]
        }
    ]
    validated_genuine = AIService.validate_source_refs(
        genuine_generated_questions, 
        retrieved_chunks, 
        expected_clerk_user_id=user_alice,
        expected_material_id=material_id_1
    )
    assert len(validated_genuine) == 1, "Test 9A Failed: Genuine chunk reference should be accepted"
    assert validated_genuine[0]["source_refs"][0]["chunk_id"] == chunk_1.chunk_id

    # Case B: LLM hallucinated / invented chunk_id
    hallucinated_questions = [
        {
            "question_text": "What is reinforcement learning?",
            "options": ["Reward maximization", "Unsupervised learning", "Sorting", "Hashing"],
            "correct_option_index": 0,
            "source_refs": [{"chunk_id": "hallucinated_chunk_9999_fake"}]
        }
    ]
    validated_hallucinated = AIService.validate_source_refs(
        hallucinated_questions,
        retrieved_chunks,
        expected_clerk_user_id=user_alice,
        expected_material_id=material_id_1
    )
    assert len(validated_hallucinated) == 0, "Test 9B Failed: Hallucinated chunk reference MUST be rejected!"

    # Case C: Chunk belonging to another user / another material
    alien_questions = [
        {
            "question_text": "What is backpropagation?",
            "options": ["Gradient calculation", "Forward pass", "Random step", "None"],
            "correct_option_index": 0,
            "source_refs": [{"chunk_id": chunk_1.chunk_id}]
        }
    ]
    validated_wrong_user = AIService.validate_source_refs(
        alien_questions,
        retrieved_chunks,
        expected_clerk_user_id=user_bob, # Wrong user
        expected_material_id=material_id_1
    )
    assert len(validated_wrong_user) == 0, "Test 9C Failed: Chunk from another user MUST be rejected!"

    print("  -> Passed! Source validation verified:")
    print("     - Genuine chunk reference: ACCEPTED")
    print("     - Hallucinated chunk reference: REJECTED")
    print("     - Wrong-user chunk reference: REJECTED")

    print("\n==================================================================")
    print("ALL 9 PHASE 24 RAG AND INGESTION TESTS PASSED SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
