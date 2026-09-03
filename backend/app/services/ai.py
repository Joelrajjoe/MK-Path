import logging
import json
import asyncio
import time
import requests
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from ..config import settings

logger = logging.getLogger("mkpath.ai")

# --- Pydantic Validation Schemas ---

class ConceptSchema(BaseModel):
    name: str = Field(description="Name of the concept")
    description: str = Field(description="Concise description/explanation of the concept")
    difficulty: str = Field(description="Difficulty level of the concept (basic, intermediate, or advanced)")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite concept names")
    exam_relevance: int = Field(description="Exam relevance score from 0 to 100")
    industry_relevance: int = Field(description="Industry relevance score from 0 to 100")

class RelationshipSchema(BaseModel):
    source: str = Field(description="Name of the source prerequisite concept")
    target: str = Field(description="Name of the target dependent concept")
    relationship_type: str = Field(description="Type of relationship, usually prerequisite_of or builds_on")

class ConceptExtractionOutput(BaseModel):
    concepts: List[ConceptSchema]
    relationships: List[RelationshipSchema]

class QuestionSchema(BaseModel):
    concept_id: str = Field(description="Database concept identifier (concept ID)")
    concept_name: str = Field(description="Name of the concept")
    question_text: str = Field(description="Multiple choice question text")
    options: List[str] = Field(description="List of exactly 4 multiple choice options")
    correct_option_index: int = Field(description="Zero-based index of correct option in the options array (0 to 3)")
    difficulty: str = Field(description="Difficulty of the question (basic, intermediate, or advanced)")
    explanation: str = Field(description="Concise explanation of the correct answer")

class QuestionGenerationOutput(BaseModel):
    questions: List[QuestionSchema]

class FlashcardItemSchema(BaseModel):
    concept_name: str = Field(description="Concept this flashcard belongs to")
    front: str = Field(description="Clear, challenging active recall question or prompt")
    back: str = Field(description="Accurate, high-yield explanation, definition, or answer")
    card_type: str = Field("standard", description="standard, cloze, code, scenario")
    difficulty: str = Field("basic", description="basic, intermediate, or advanced")

class FlashcardGenerationOutput(BaseModel):
    flashcards: List[FlashcardItemSchema]


# --- OOP Provider Abstraction ---

class AIProvider:
    async def extract_concepts_and_relationships(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError()

    async def generate_questions_for_concepts(self, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError()


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    async def extract_concepts_and_relationships(self, text: str) -> Dict[str, Any]:
        prompt = (
            "You are MK-Path's grounded learning assistant. "
            "Use ONLY the supplied retrieved source context for factual claims about the user's uploaded material. "
            "Do not invent facts, concepts, or relationships. If the supplied retrieved sources are insufficient, "
            "return INSUFFICIENT_SOURCE_CONTENT. "
            "Analyze the following study material and extract all key educational concepts and their relationships.\n\n"
            f"Study material text:\n{text}"
        )
        
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ConceptExtractionOutput,
                temperature=0.1
            )
        )
        
        raw_res = response.text
        data = json.loads(raw_res)
        return data

    async def generate_questions_for_concepts(self, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept Name: {c['name']} (ID: {c['_id'] if '_id' in c else c.get('id')})\n"
            f"  Description: {c['description']}\n"
            f"  Difficulty: {c['difficulty']}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Material Context:\n" + "\n---\n".join(context_chunks)

        profile_block = ""
        if user_profile:
            profile_block = (
                f"\n\nStudent Profile:\n"
                f"- Target Difficulty: {user_profile.get('preferred_difficulty', 'intermediate')}\n"
                f"- Learning Goal: {user_profile.get('learning_goal', 'General understanding')}\n"
                f"- Target Role: {user_profile.get('target_role', 'Not specified')}"
            )
        
        prompt = (
            "You are MK-Path's grounded learning assistant. "
            f"Create exactly {num_questions} multiple choice quiz questions covering these study concepts:\n\n{concepts_block}{context_block}{profile_block}\n\n"
            "Generate questions strictly grounded in the concepts, descriptions, and supplied context. "
            "Ensure the options array has exactly 4 items, correct_option_index is between 0 and 3, and questions are educational and accurate."
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuestionGenerationOutput,
                temperature=0.2
            )
        )
        
        raw_res = response.text
        data = json.loads(raw_res)
        return data.get("questions", [])

    async def generate_flashcards(self, concepts: List[Dict[str, Any]], cards_per_concept: int = 2, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept Name: {c['name']}\n"
            f"  Description: {c.get('description', '')}\n"
            f"  Difficulty: {c.get('difficulty', 'basic')}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Material Context:\n" + "\n---\n".join(context_chunks[:6])

        prompt = (
            "You are MK-Path's active recall flashcard generation engine. "
            f"Generate high-yield, conceptual spaced-repetition flashcards ({cards_per_concept} per concept) covering:\n\n{concepts_block}{context_block}\n\n"
            "Each flashcard must have:\n"
            "- concept_name: The exact matching concept name\n"
            "- front: A crisp, engaging question, scenario, or active recall prompt\n"
            "- back: A clear, complete, high-yield explanation with bullet points if helpful\n"
            "- card_type: 'standard', 'scenario', 'cloze', or 'code'\n"
            "- difficulty: 'basic', 'intermediate', or 'advanced'\n"
            "Ensure cards test deep understanding rather than simple trivial definitions."
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FlashcardGenerationOutput,
                temperature=0.2
            )
        )
        
        raw_res = response.text
        data = json.loads(raw_res)
        return data.get("flashcards", [])

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = await asyncio.to_thread(
            self.client.models.embed_content,
            model="models/gemini-embedding-001",
            contents=texts
        )
        return [e.values for e in response.embeddings]


class GroqProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def extract_concepts_and_relationships(self, text: str) -> Dict[str, Any]:
        payload = {
            "model": "openai/gpt-oss-120b",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MK-Path's grounded learning assistant. "
                        "Use ONLY the supplied retrieved source context for factual claims about the user's uploaded material. "
                        "Do not invent facts or concepts. If the supplied retrieved sources are insufficient to answer the task, "
                        "return INSUFFICIENT_SOURCE_CONTENT. "
                        "Analyze the study material and extract all core concepts and their relationships. Return your output strictly as a JSON "
                        "object matching this structure: "
                        '{"concepts": [{"name": "Concept Name", "description": "Concept Description", '
                        '"exam_relevance": 90, "industry_relevance": 85, "difficulty": "basic", '
                        '"prerequisites": [], "source_refs": [{"chunk_id": "..."}]}], "relationships": [{"source": "Concept Name", '
                        '"target": "Another Concept", "relationship_type": "prerequisite_of", "source_refs": [{"chunk_id": "..."}]}]}. '
                        "Do not include any extra text."
                    )
                },
                {
                    "role": "user",
                    "content": f"Study material content:\n\n{text[:8000]}"
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = await asyncio.to_thread(
            requests.post,
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            return data
        else:
            raise Exception(f"Groq API error status: {response.status_code} - {response.text}")

    async def generate_questions_for_concepts(self, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept Name: {c['name']} (ID: {c['_id'] if '_id' in c else c.get('id')})\n"
            f"  Description: {c['description']}\n"
            f"  Difficulty: {c['difficulty']}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Material Context:\n" + "\n---\n".join(context_chunks)

        profile_block = ""
        if user_profile:
            profile_block = (
                f"\n\nStudent Profile:\n"
                f"- Target Difficulty: {user_profile.get('preferred_difficulty', 'intermediate')}\n"
                f"- Learning Goal: {user_profile.get('learning_goal', 'General understanding')}\n"
                f"- Target Role: {user_profile.get('target_role', 'Not specified')}"
            )
        
        payload = {
            "model": "openai/gpt-oss-120b",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MK-Path's grounded learning assistant. "
                        "Generate rigorous, high-quality multiple choice assessment questions grounded in the provided concepts, study context, and student profile. "
                        "Return your output strictly as a JSON object matching this structure: "
                        '{"questions": [{"concept_id": "concept_database_id", "concept_name": "concept_name", '
                        '"question_text": "question prompt", "options": ["Option A", "Option B", "Option C", "Option D"], '
                        '"correct_option_index": 0, "difficulty": "basic", "explanation": "justification", "source_refs": []}]}. '
                        "Do not output plain text or markdown outside of the valid JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": f"Concepts list:\n{concepts_block}{context_block}{profile_block}\n\nGenerate exactly {num_questions} questions."
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = await asyncio.to_thread(
            requests.post,
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            return data.get("questions", [])
        else:
            raise Exception(f"Groq API error status: {response.status_code} - {response.text}")

    async def generate_flashcards(self, concepts: List[Dict[str, Any]], cards_per_concept: int = 2, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept Name: {c['name']}\n"
            f"  Description: {c.get('description', '')}\n"
            f"  Difficulty: {c.get('difficulty', 'basic')}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Material Context:\n" + "\n---\n".join(context_chunks[:6])

        payload = {
            "model": "openai/gpt-oss-120b",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MK-Path's active recall flashcard generation engine. "
                        "Return your output strictly as a JSON object matching this structure: "
                        '{"flashcards": [{"concept_name": "name", "front": "question/prompt", "back": "answer/explanation", "card_type": "standard", "difficulty": "basic"}]}. '
                        "Do not output plain text or markdown outside of the JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": f"Generate {cards_per_concept} flashcards per concept covering:\n{concepts_block}{context_block}"
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = await asyncio.to_thread(
            requests.post,
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            return data.get("flashcards", [])
        else:
            raise Exception(f"Groq Flashcard API error: {response.status_code} - {response.text}")


class LocalFallbackProvider(AIProvider):
    async def extract_concepts_and_relationships(self, text: str) -> Dict[str, Any]:
        return {"error": "INSUFFICIENT_SOURCE_CONTENT", "message": "Local fallback cannot generate grounded concepts."}

    async def generate_questions_for_concepts(self, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        return []

    async def generate_flashcards(self, concepts: List[Dict[str, Any]], cards_per_concept: int = 2, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        # Deterministic card generation fallback based on concept name & description
        cards = []
        for c in concepts:
            cards.append({
                "concept_name": c["name"],
                "front": f"What is the core definition and primary purpose of {c['name']}?",
                "back": c.get("description", f"Key concept in curriculum: {c['name']}."),
                "card_type": "standard",
                "difficulty": c.get("difficulty", "basic")
            })
            if c.get("prerequisites"):
                cards.append({
                    "concept_name": c["name"],
                    "front": f"What foundational concepts are required before studying {c['name']}?",
                    "back": f"Prerequisites: {', '.join(c['prerequisites'])}.",
                    "card_type": "standard",
                    "difficulty": "intermediate"
                })
        return cards


# --- Routing Service Orchestration Layer ---

class AIService:
    @staticmethod
    def clean_json_string(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    @classmethod
    async def extract_concepts_and_relationships(cls, text: str) -> Dict[str, Any]:
        """
        Extracts educational concepts and dependency relationships from text.
        Cycles through Gemini API Keys -> Groq API Key -> Local Parser Fallback.
        Applies Pydantic validations and observability logging.
        """
        gemini_keys = settings.GEMINI_API_KEYS
        gemini_model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        
        # Stage 1: Gemini
        if gemini_keys:
            for idx, key in enumerate(gemini_keys):
                start_time = time.perf_counter()
                provider = "Gemini"
                model_name = gemini_model
                success = False
                error_category = "None"
                
                try:
                    provider_obj = GeminiProvider(api_key=key, model_name=model_name)
                    data = await provider_obj.extract_concepts_and_relationships(text)
                    
                    # Validate output using Pydantic
                    validated = ConceptExtractionOutput(**data)
                    data_dict = validated.model_dump()
                    success = True
                    
                    cls._log_observability(
                        operation="extract_concepts",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return data_dict
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="extract_concepts",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini concept extraction failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                data = await provider_obj.extract_concepts_and_relationships(text)
                
                # Validate output
                validated = ConceptExtractionOutput(**data)
                data_dict = validated.model_dump()
                success = True
                
                cls._log_observability(
                    operation="extract_concepts",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return data_dict
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="extract_concepts",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq concept extraction fallback failed: {e}")

        # Stage 3: Local Fallback
        start_time = time.perf_counter()
        provider = "Local"
        model_name = "RuleBasedKeywordHeuristic"
        success = True
        error_category = "None"
        
        try:
            provider_obj = LocalFallbackProvider()
            data = await provider_obj.extract_concepts_and_relationships(text)
            
            cls._log_observability(
                operation="extract_concepts",
                provider=provider,
                model=model_name,
                success=success,
                latency=time.perf_counter() - start_time,
                fallback_used=True,
                error_category=error_category
            )
            return data
        except Exception as e:
            logger.error(f"Local concept extraction fallback failed catastrophically: {e}")
            return {"concepts": [], "relationships": []}

    @classmethod
    async def generate_questions_for_concepts(cls, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generates MCQs for a list of concepts.
        Cycles through Gemini -> Groq -> Local Fallback.
        Applies Pydantic validations and observability logging.
        """
        gemini_keys = settings.GEMINI_API_KEYS
        gemini_model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        
        # Stage 1: Gemini
        if gemini_keys:
            for idx, key in enumerate(gemini_keys):
                start_time = time.perf_counter()
                provider = "Gemini"
                model_name = gemini_model
                success = False
                error_category = "None"
                
                try:
                    provider_obj = GeminiProvider(api_key=key, model_name=model_name)
                    questions = await provider_obj.generate_questions_for_concepts(concepts, num_questions, user_profile, context_chunks)
                    
                    # Validate output using Pydantic schema
                    validated = QuestionGenerationOutput(questions=questions)
                    data_list = validated.model_dump()["questions"]
                    success = True
                    
                    cls._log_observability(
                        operation="generate_questions",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return data_list
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="generate_questions",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini MCQ generation failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                questions = await provider_obj.generate_questions_for_concepts(concepts, num_questions, user_profile, context_chunks)
                
                # Validate output
                validated = QuestionGenerationOutput(questions=questions)
                data_list = validated.model_dump()["questions"]
                success = True
                
                cls._log_observability(
                    operation="generate_questions",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return data_list
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="generate_questions",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq question generation fallback failed: {e}")

        # Stage 3: Local Fallback
        start_time = time.perf_counter()
        provider = "Local"
        model_name = "RuleBasedDistractorMCQ"
        success = True
        error_category = "None"
        
        try:
            provider_obj = LocalFallbackProvider()
            questions = await provider_obj.generate_questions_for_concepts(concepts, num_questions, user_profile, context_chunks)
            
            cls._log_observability(
                operation="generate_questions",
                provider=provider,
                model=model_name,
                success=success,
                latency=time.perf_counter() - start_time,
                fallback_used=True,
                error_category=error_category
            )
            return questions
        except Exception as e:
            logger.error(f"Local question generation fallback failed catastrophically: {e}")
            return []

    @classmethod
    async def generate_flashcards(cls, concepts: List[Dict[str, Any]], cards_per_concept: int = 2, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generates active-recall flashcards for concepts.
        Cycles through Gemini -> Groq -> Local Fallback.
        """
        gemini_keys = settings.GEMINI_API_KEYS
        gemini_model = settings.GEMINI_MODEL or "gemini-3.5-flash"
        
        # Stage 1: Gemini
        if gemini_keys:
            for idx, key in enumerate(gemini_keys):
                start_time = time.perf_counter()
                provider = "Gemini"
                model_name = gemini_model
                success = False
                error_category = "None"
                
                try:
                    provider_obj = GeminiProvider(api_key=key, model_name=model_name)
                    cards = await provider_obj.generate_flashcards(concepts, cards_per_concept, context_chunks)
                    success = True
                    
                    cls._log_observability(
                        operation="generate_flashcards",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return cards
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="generate_flashcards",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini Flashcard generation failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                cards = await provider_obj.generate_flashcards(concepts, cards_per_concept, context_chunks)
                success = True
                
                cls._log_observability(
                    operation="generate_flashcards",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return cards
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="generate_flashcards",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq flashcard generation fallback failed: {e}")

        # Stage 3: Local Fallback
        start_time = time.perf_counter()
        provider = "Local"
        model_name = "RuleBasedFlashcard"
        success = True
        error_category = "None"
        
        try:
            provider_obj = LocalFallbackProvider()
            cards = await provider_obj.generate_flashcards(concepts, cards_per_concept, context_chunks)
            
            cls._log_observability(
                operation="generate_flashcards",
                provider=provider,
                model=model_name,
                success=success,
                latency=time.perf_counter() - start_time,
                fallback_used=True,
                error_category=error_category
            )
            return cards
        except Exception as e:
            logger.error(f"Local flashcard generation fallback failed catastrophically: {e}")
            return []

    @classmethod
    async def generate_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for semantic search using Gemini.
        """
        gemini_keys = settings.GEMINI_API_KEYS
        if gemini_keys:
            key = gemini_keys[0] # Just use the first key
            provider_obj = GeminiProvider(api_key=key, model_name="models/gemini-embedding-001")
            try:
                embeddings = await provider_obj.generate_embeddings(texts)
                return embeddings
            except Exception as e:
                logger.error(f"Failed to generate embeddings via Gemini: {e}")
        
        # Fallback to zeros (no search) if API fails
        logger.warning("Falling back to empty embeddings.")
        return [[0.0] * 768 for _ in texts]
        
    @staticmethod
    def _categorize_error(e: Exception) -> str:
        """Categorizes exception into standard logging terms."""
        from pydantic import ValidationError
        err_msg = str(e).lower()
        if isinstance(e, ValidationError):
            return "SchemaValidationError"
        elif "api key" in err_msg or "apikey" in err_msg or "invalid key" in err_msg:
            return "APIKeyError"
        elif "rate limit" in err_msg or "quota" in err_msg or "429" in err_msg:
            return "RateLimitError"
        elif "timeout" in err_msg or "connection" in err_msg or "network" in err_msg:
            return "NetworkError"
        return "Other"

    @staticmethod
    def _log_observability(operation: str, provider: str, model: str, success: bool, latency: float, fallback_used: bool, error_category: str):
        """Outputs structured observability event logs securely."""
        log_entry = {
            "event": "ai_observability_metric",
            "operation": operation,
            "provider": provider,
            "model": model,
            "success": success,
            "latency_seconds": round(latency, 4),
            "fallback_used": fallback_used,
            "error_category": error_category,
            "timestamp": time.time()
        }
        logger.info(json.dumps(log_entry))

    @staticmethod
    def validate_source_refs(generated_items: List[Dict[str, Any]], retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validates that every source_ref returned by the LLM actually exists in the retrieved chunks.
        Removes invalid items to prevent hallucinated grounding.
        """
        valid_items = []
        valid_chunk_ids = {str(c.get("chunk_id")) for c in retrieved_chunks if c.get("chunk_id")}
        
        for item in generated_items:
            refs = item.get("source_refs", [])
            if not refs:
                # Reject items that have no source references at all
                continue
                
            has_valid_ref = False
            for ref in refs:
                ref_id = str(ref.get("chunk_id", ""))
                if ref_id in valid_chunk_ids:
                    has_valid_ref = True
                    break
                    
            if has_valid_ref:
                valid_items.append(item)
                
        return valid_items
