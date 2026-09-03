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

class MindMapSubChildSchema(BaseModel):
    id: str = Field(description="Unique leaf identifier e.g. leaf_1")
    label: str = Field(description="Subtopic or property title")
    details: Optional[str] = Field(None, description="Short 1-sentence note")

class MindMapBranchSchema(BaseModel):
    id: str = Field(description="Unique branch identifier e.g. branch_1")
    label: str = Field(description="Branch or section category title")
    details: Optional[str] = Field(None, description="Short summary of this branch")
    children: List[MindMapSubChildSchema] = Field(default_factory=list, description="Sub-elements of this branch")

class MindMapRootSchema(BaseModel):
    id: str = Field(default="root", description="Root identifier")
    label: str = Field(description="Concept name as root title")
    details: Optional[str] = Field(None, description="Overview note")
    children: List[MindMapBranchSchema] = Field(default_factory=list, description="Top-level subtopics and branches")

class StudyNoteItemSchema(BaseModel):
    concept_name: str = Field(description="Target concept name")
    title: str = Field(description="Engaging title for the study module")
    summary: str = Field(description="High-level 2-3 sentence conceptual executive summary")
    key_takeaways: List[str] = Field(description="3-5 bullet points of core principles")
    formulae_or_rules: List[str] = Field(description="Key equations, syntax, or theoretical rules")
    common_pitfalls: List[str] = Field(description="2-3 common misconceptions or exam traps")
    markdown_content: str = Field(description="Rich markdown formatted structured study notes with code blocks/examples if applicable")
    mind_map_tree: MindMapRootSchema = Field(description="Hierarchical mind-map tree with root, branches and child leaves")

class StudyNotesGenerationOutput(BaseModel):
    notes: List[StudyNoteItemSchema]

class PodcastDialogueTurnSchema(BaseModel):
    speaker: str = Field(description="'Alex' (deep-dive lead researcher) or 'Sam' (curious analytical co-host)")
    text: str = Field(description="Spoken conversation line")
    emotion: Optional[str] = Field("enthusiastic", description="enthusiastic, questioning, explanatory, humorous")

class PodcastGenerationOutput(BaseModel):
    title: str = Field(description="Catchy, engaging podcast episode title")
    summary: str = Field(description="1-2 sentence executive overview of the episode")
    script: List[PodcastDialogueTurnSchema] = Field(description="10-18 dynamic alternating conversational dialogue turns between Alex and Sam")


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

    async def generate_study_notes(self, concepts: List[Dict[str, Any]], depth: str = "comprehensive", context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept: {c['name']}\n"
            f"  Description: {c.get('description', '')}\n"
            f"  Difficulty: {c.get('difficulty', 'basic')}\n"
            f"  Prerequisites: {', '.join(c.get('prerequisites', []))}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Material Context:\n" + "\n---\n".join(context_chunks[:8])

        prompt = (
            "You are MK-Path's master educational synthesizer and mind-map architect. "
            f"Generate structured, high-yield study notes with a visual hierarchical mind-map tree for each of these concepts:\n\n{concepts_block}{context_block}\n\n"
            "For each concept, produce:\n"
            "- concept_name: The exact concept name\n"
            "- title: Engaging title for this learning module\n"
            "- summary: A crisp 2-3 sentence conceptual executive summary\n"
            "- key_takeaways: 3-5 high-yield bullet principles\n"
            "- formulae_or_rules: Key mathematical formulas, code patterns, or theoretical axioms\n"
            "- common_pitfalls: 2-3 student misconceptions or exam traps\n"
            "- markdown_content: Beautifully formatted Markdown notes with subheadings, explanations, and practical illustrations\n"
            "- mind_map_tree: A recursive JSON tree where root is {'id': 'root', 'label': concept_name, 'children': [{'id': 'c1', 'label': 'Branch Title', 'details': 'summary', 'children': [...]}]}"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StudyNotesGenerationOutput,
                temperature=0.2
            )
        )
        
        raw_res = response.text
        data = json.loads(raw_res)
        return data.get("notes", [])

    async def socratic_chat(
        self,
        messages: List[Dict[str, str]],
        concept_name: Optional[str] = None,
        context_chunks: List[str] = None,
        tutor_mode: str = "socratic",
        mastery_category: str = "Learning"
    ) -> str:
        """Interactive 1-on-1 Socratic AI tutoring grounded in retrieved chunks & concept."""
        context_block = ""
        if context_chunks:
            context_block = "\n\nGrounding Knowledge Base:\n" + "\n---\n".join(context_chunks[:6])
            
        system_instructions = (
            "You are MK-Path's elite Socratic AI Tutor & Concept Guide. "
            f"You are tutoring a student on the subject/concept: '{concept_name or 'General Curriculum'}'. "
            f"The learner's current mastery state is: {mastery_category}.\n"
            f"Tutor Mode: {tutor_mode.upper()}.\n\n"
            "Pedagogical Guidelines:\n"
            "1. If mode is SOCRATIC: Guide the student through thoughtful questions, leading hints, analogies, and active inquiry rather than giving direct answers immediately.\n"
            "2. If mode is DIRECT_EXPLAINER: Deliver crystal-clear explanations with analogies, code snippets, and structural breakdowns.\n"
            "3. If mode is EXAM_COACH: Challenge the student with rapid test scenarios, edge cases, and misconception diagnosis.\n"
            "4. Ground all explanations strictly in the uploaded curriculum context whenever available.\n"
            "5. Use Markdown formatting (bold keywords, bullet lists, code fences) for high legibility."
            f"{context_block}"
        )

        conversation_history = "\n".join([
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in messages
        ])

        full_prompt = f"{system_instructions}\n\n--- Conversation History ---\n{conversation_history}\n\nAssistant:"

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        return response.text or "I'm ready to guide your inquiry. What concept would you like to explore?"

    async def generate_podcast(
        self,
        material_title: str,
        concepts: List[Dict[str, Any]],
        context_chunks: List[str],
        style: str = "dynamic"
    ) -> Dict[str, Any]:
        """Generate a two-host deep-dive audio podcast episode script."""
        concepts_block = "\n".join([f"- {c['name']}: {c.get('description', '')}" for c in concepts[:8]])
        context_block = "\n---\n".join(context_chunks[:10])

        prompt = (
            "You are MK-Path's audio podcast generation director (inspired by Google NotebookLM Audio Overviews). "
            f"Generate a captivating two-host podcast episode discussing the study material: '{material_title}'.\n\n"
            f"Key Concepts to Explore:\n{concepts_block}\n\n"
            f"Source Text Context:\n{context_block}\n\n"
            "Format Requirements:\n"
            "1. Two dynamic hosts: 'Alex' (lead conceptual investigator, provides deep analogies) and 'Sam' (curious co-host, asks provocative questions and connects concepts to real life).\n"
            "2. Make the conversation natural, entertaining, intellectual, and grounded in the source text.\n"
            "3. Include 12-16 alternating dialogue turns.\n"
            "4. Output strictly structured JSON matching PodcastGenerationOutput."
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PodcastGenerationOutput,
                temperature=0.4
            )
        )
        
        raw_res = response.text
        data = json.loads(raw_res)
        return data

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

    async def generate_study_notes(self, concepts: List[Dict[str, Any]], depth: str = "comprehensive", context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        concepts_block = "\n".join([
            f"- Concept: {c['name']}\n"
            f"  Description: {c.get('description', '')}\n"
            f"  Difficulty: {c.get('difficulty', 'basic')}\n"
            f"  Prerequisites: {', '.join(c.get('prerequisites', []))}"
            for c in concepts
        ])
        
        context_block = ""
        if context_chunks:
            context_block = "\n\nSource Context:\n" + "\n---\n".join(context_chunks[:6])

        payload = {
            "model": "openai/gpt-oss-120b",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MK-Path's master educational synthesizer. "
                        "Return your output strictly as a JSON object matching this structure: "
                        '{"notes": [{"concept_name": "name", "title": "Module Title", "summary": "2-sentence summary", "key_takeaways": ["point 1", "point 2"], "formulae_or_rules": ["rule 1"], "common_pitfalls": ["trap 1"], "markdown_content": "# Detailed Notes...", "mind_map_tree": {"id": "root", "label": "Concept", "children": [{"id": "c1", "label": "Subtopic", "details": "desc", "children": []}]}}]}.'
                    )
                },
                {
                    "role": "user",
                    "content": f"Generate structured study notes and mind-map trees for:\n{concepts_block}{context_block}"
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
            timeout=25
        )

        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            data = json.loads(content)
            return data.get("notes", [])
        else:
            raise Exception(f"Groq Study Notes API error: {response.status_code} - {response.text}")

    async def socratic_chat(
        self,
        messages: List[Dict[str, str]],
        concept_name: Optional[str] = None,
        context_chunks: List[str] = None,
        tutor_mode: str = "socratic",
        mastery_category: str = "Learning"
    ) -> str:
        context_block = ""
        if context_chunks:
            context_block = "\n\nGrounding Context:\n" + "\n---\n".join(context_chunks[:6])

        system_msg = (
            "You are MK-Path's Socratic AI Tutor & Concept Guide. "
            f"Concept target: '{concept_name or 'General Curriculum'}'. Mode: {tutor_mode}. "
            "Guide the student thoughtfully, test their understanding with interactive inquiries, and ground explanations in their study materials."
            f"{context_block}"
        )

        groq_messages = [{"role": "system", "content": system_msg}]
        for m in messages:
            groq_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })

        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": groq_messages,
            "temperature": 0.3
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
            timeout=20
        )

        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Groq Tutor API error: {response.status_code} - {response.text}")

    async def generate_podcast(
        self,
        material_title: str,
        concepts: List[Dict[str, Any]],
        context_chunks: List[str],
        style: str = "dynamic"
    ) -> Dict[str, Any]:
        concepts_block = "\n".join([f"- {c['name']}: {c.get('description', '')}" for c in concepts[:8]])
        context_block = "\n---\n".join(context_chunks[:6])

        payload = {
            "model": "openai/gpt-oss-120b",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are MK-Path's audio podcast generator. "
                        "Return strictly a JSON object with: 'title' (string), 'summary' (string), and 'script' (list of alternating {'speaker': 'Alex'|'Sam', 'text': string, 'emotion': string}). "
                        "Make the discussion entertaining, analytical and educational."
                    )
                },
                {
                    "role": "user",
                    "content": f"Generate a two-host podcast discussing '{material_title}'. Concepts:\n{concepts_block}\nContext:\n{context_block}"
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
            timeout=25
        )

        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            raise Exception(f"Groq Podcast API error: {response.status_code} - {response.text}")


class LocalFallbackProvider(AIProvider):
    async def extract_concepts_and_relationships(self, text: str) -> Dict[str, Any]:
        return {"error": "INSUFFICIENT_SOURCE_CONTENT", "message": "Local fallback cannot generate grounded concepts."}

    async def generate_questions_for_concepts(self, concepts: List[Dict[str, Any]], num_questions: int, user_profile: dict = None, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        return []

    async def generate_flashcards(self, concepts: List[Dict[str, Any]], cards_per_concept: int = 2, context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        cards = []
        for c in concepts:
            cards.append({
                "concept_name": c["name"],
                "front": f"What is the core definition and primary purpose of {c['name']}?",
                "back": c.get("description", f"Key concept in curriculum: {c['name']}."),
                "card_type": "standard",
                "difficulty": c.get("difficulty", "basic")
            })
        return cards

    async def generate_podcast(
        self,
        material_title: str,
        concepts: List[Dict[str, Any]],
        context_chunks: List[str],
        style: str = "dynamic"
    ) -> Dict[str, Any]:
        turns = [
            {"speaker": "Alex", "text": f"Welcome to today's MK-Path deep-dive! Today we're exploring {material_title}.", "emotion": "enthusiastic"},
            {"speaker": "Sam", "text": "I've been looking forward to this one. What makes these concepts so essential?", "emotion": "questioning"}
        ]
        for c in concepts[:3]:
            turns.append({"speaker": "Alex", "text": f"Let's look at {c['name']}. {c.get('description', 'This is a foundational concept.')}", "emotion": "explanatory"})
            turns.append({"speaker": "Sam", "text": f"That makes total sense. So how does {c['name']} connect with practical real-world problems?", "emotion": "questioning"})
            turns.append({"speaker": "Alex", "text": f"When applied correctly, it prevents common pitfalls and establishes structured mental models.", "emotion": "enthusiastic"})
        turns.append({"speaker": "Sam", "text": "That's a wrap on this overview! Time to test our mastery in the assessment module.", "emotion": "enthusiastic"})
        
        return {
            "title": f"Deep Dive: {material_title}",
            "summary": f"An audio exploration of {len(concepts)} key curriculum concepts.",
            "script": turns
        }

    async def socratic_chat(
        self,
        messages: List[Dict[str, str]],
        concept_name: Optional[str] = None,
        context_chunks: List[str] = None,
        tutor_mode: str = "socratic",
        mastery_category: str = "Learning"
    ) -> str:
        return (
            f"Hello! I am your MK-Path Socratic Tutor for **{concept_name or 'your curriculum'}**. "
            "To test your foundational understanding: How would you describe the core objective of this concept in your own words?"
        )

    async def generate_study_notes(self, concepts: List[Dict[str, Any]], depth: str = "comprehensive", context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        notes = []
        for c in concepts:
            name = c["name"]
            desc = c.get("description", f"Core educational concept: {name}")
            notes.append({
                "concept_name": name,
                "title": f"Comprehensive Master Notes: {name}",
                "summary": desc,
                "key_takeaways": [
                    f"Understanding foundational properties of {name}",
                    f"Applying {name} in real-world scenarios",
                    f"Connecting {name} with related prerequisite concepts"
                ],
                "formulae_or_rules": [
                    f"Rule 1: Always verify assumptions before applying {name}."
                ],
                "common_pitfalls": [
                    f"Confusing {name} with adjacent high-level primitives."
                ],
                "markdown_content": f"# {name}\n\n## Overview\n{desc}\n\n## Core Principles\n- Applied systematically across the curriculum.\n- Requires understanding of prerequisites: {', '.join(c.get('prerequisites', [])) or 'None'}.",
                "mind_map_tree": {
                    "id": "root",
                    "label": name,
                    "details": desc,
                    "children": [
                        {
                            "id": "branch_1",
                            "label": "Core Definition",
                            "details": desc,
                            "children": []
                        },
                        {
                            "id": "branch_2",
                            "label": "Prerequisites & Dependencies",
                            "details": f"Prerequisites: {', '.join(c.get('prerequisites', [])) or 'None'}",
                            "children": []
                        }
                    ]
                }
            })
        return notes


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
    async def generate_study_notes(cls, concepts: List[Dict[str, Any]], depth: str = "comprehensive", context_chunks: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generates structured study notes and hierarchical mind-map trees for concepts.
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
                    notes = await provider_obj.generate_study_notes(concepts, depth, context_chunks)
                    success = True
                    
                    cls._log_observability(
                        operation="generate_study_notes",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return notes
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="generate_study_notes",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini Study Notes generation failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                notes = await provider_obj.generate_study_notes(concepts, depth, context_chunks)
                success = True
                
                cls._log_observability(
                    operation="generate_study_notes",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return notes
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="generate_study_notes",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq study notes fallback failed: {e}")

        # Stage 3: Local Fallback
        start_time = time.perf_counter()
        provider = "Local"
        model_name = "RuleBasedStudyNotes"
        success = True
        error_category = "None"
        
        try:
            provider_obj = LocalFallbackProvider()
            notes = await provider_obj.generate_study_notes(concepts, depth, context_chunks)
            
            cls._log_observability(
                operation="generate_study_notes",
                provider=provider,
                model=model_name,
                success=success,
                latency=time.perf_counter() - start_time,
                fallback_used=True,
                error_category=error_category
            )
            return notes
        except Exception as e:
            logger.error(f"Local study notes fallback failed: {e}")
            return []

    @classmethod
    async def socratic_chat(
        cls,
        messages: List[Dict[str, str]],
        concept_name: Optional[str] = None,
        context_chunks: List[str] = None,
        tutor_mode: str = "socratic",
        mastery_category: str = "Learning"
    ) -> str:
        """
        Orchestrates 1-on-1 Socratic conversational tutoring.
        Cycles through Gemini -> Groq -> Local fallback.
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
                    response_text = await provider_obj.socratic_chat(
                        messages=messages,
                        concept_name=concept_name,
                        context_chunks=context_chunks,
                        tutor_mode=tutor_mode,
                        mastery_category=mastery_category
                    )
                    success = True
                    cls._log_observability(
                        operation="socratic_chat",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return response_text
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="socratic_chat",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini Socratic Chat failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                response_text = await provider_obj.socratic_chat(
                    messages=messages,
                    concept_name=concept_name,
                    context_chunks=context_chunks,
                    tutor_mode=tutor_mode,
                    mastery_category=mastery_category
                )
                success = True
                cls._log_observability(
                    operation="socratic_chat",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return response_text
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="socratic_chat",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq Socratic Chat fallback failed: {e}")

        # Stage 3: Local Fallback
        try:
            provider_obj = LocalFallbackProvider()
            return await provider_obj.socratic_chat(
                messages=messages,
                concept_name=concept_name,
                context_chunks=context_chunks,
                tutor_mode=tutor_mode,
                mastery_category=mastery_category
            )
        except Exception as e:
            logger.error(f"Local Socratic chat fallback failed: {e}")
            return f"Let's focus on **{concept_name or 'your topic'}**. How can I help clarify this concept?"

    @classmethod
    async def generate_podcast(
        cls,
        material_title: str,
        concepts: List[Dict[str, Any]],
        context_chunks: List[str],
        style: str = "dynamic"
    ) -> Dict[str, Any]:
        """
        Synthesizes a NotebookLM-style multi-speaker deep-dive podcast episode.
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
                    podcast_data = await provider_obj.generate_podcast(
                        material_title=material_title,
                        concepts=concepts,
                        context_chunks=context_chunks,
                        style=style
                    )
                    success = True
                    cls._log_observability(
                        operation="generate_podcast",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=False,
                        error_category=error_category
                    )
                    return podcast_data
                except Exception as e:
                    success = False
                    error_category = cls._categorize_error(e)
                    cls._log_observability(
                        operation="generate_podcast",
                        provider=provider,
                        model=model_name,
                        success=success,
                        latency=time.perf_counter() - start_time,
                        fallback_used=True,
                        error_category=error_category
                    )
                    logger.error(f"Gemini Podcast generation failed (Key {idx+1}/{len(gemini_keys)}): {e}")

        # Stage 2: Groq Fallback
        if settings.GROQ_API_KEY:
            start_time = time.perf_counter()
            provider = "Groq"
            model_name = "openai/gpt-oss-120b"
            success = False
            error_category = "None"
            
            try:
                provider_obj = GroqProvider(api_key=settings.GROQ_API_KEY)
                podcast_data = await provider_obj.generate_podcast(
                    material_title=material_title,
                    concepts=concepts,
                    context_chunks=context_chunks,
                    style=style
                )
                success = True
                cls._log_observability(
                    operation="generate_podcast",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                return podcast_data
            except Exception as e:
                success = False
                error_category = cls._categorize_error(e)
                cls._log_observability(
                    operation="generate_podcast",
                    provider=provider,
                    model=model_name,
                    success=success,
                    latency=time.perf_counter() - start_time,
                    fallback_used=True,
                    error_category=error_category
                )
                logger.error(f"Groq Podcast fallback failed: {e}")

        # Stage 3: Local Fallback
        provider_obj = LocalFallbackProvider()
        return await provider_obj.generate_podcast(
            material_title=material_title,
            concepts=concepts,
            context_chunks=context_chunks,
            style=style
        )

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
