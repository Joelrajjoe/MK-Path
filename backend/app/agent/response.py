"""
MK-Path 2.0 Response Engine
Synthesizes agent responses with Gemini, Groq fallback, citations, and action recommendations.
"""
import logging
import asyncio
import requests
import json
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from ..config import settings
from .models import (
    LearnerContext, AgentIntent, AgentChatMessage, SourceCitation,
    SourceCategory
)
from .policies import AgentPolicies
from .citations import CitationBuilder

logger = logging.getLogger("mkpath.agent.response")

class AgentResponseEngine:
    """
    Executes grounded synthesis using Gemini primary and Groq fallback.
    """

    @classmethod
    async def generate_response(
        cls,
        context: LearnerContext,
        conversation_history: List[AgentChatMessage],
        user_message: str,
        intent: AgentIntent
    ) -> AgentChatMessage:
        """
        Synthesizes grounded agent message with citations.
        """
        # 1. Build prompt payload
        prompt = cls._build_synthesis_prompt(context, user_message, intent)
        system_instruction = AgentPolicies.SYSTEM_BASE_PROMPT + "\n\n" + AgentPolicies.get_intent_directive(intent)

        citations: List[SourceCitation] = []
        action_suggestion: Optional[Dict[str, Any]] = None

        # Build citations from grounded chunks
        for chunk in context.grounded_chunks:
            citations.append(CitationBuilder.from_material_chunk(chunk))

        # Build citations from active learner state
        if context.mastery:
            top_m = context.mastery[0]
            citations.append(CitationBuilder.from_learner_state(
                top_m.get("concept_name", "Concept"),
                f"{Math_round(top_m.get('mastery_score', 0))}%",
                "Calculated via confidence-corrected BKT"
            ))

        # Build citations from web intelligence
        for w in context.web_knowledge:
            citations.append(CitationBuilder.from_web_source(
                w.get("topic", "Industry Intelligence"),
                "https://roadmap.sh/ai",
                w.get("standards", "")
            ))

        # 2. Call Gemini Primary
        content_text = None
        gemini_keys = settings.GEMINI_API_KEYS or ([settings.GEMINI_API_KEY] if settings.GEMINI_API_KEY else [])

        for key in gemini_keys:
            try:
                client = genai.Client(api_key=key)
                model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
                
                # Format conversation history
                contents = []
                for msg in conversation_history[-4:]:
                    role = "user" if msg.role == "user" else "model"
                    contents.append(f"{role.upper()}: {msg.content}")

                contents.append(f"USER: {user_message}\n\n[CONTEXT DOSSIER]:\n{prompt}")

                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents="\n\n".join(contents),
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )
                if response and response.text:
                    content_text = response.text
                    break
            except Exception as e:
                logger.warning(f"Gemini Agent synthesis error: {e}")

        # 3. Fallback to Groq if Gemini fails
        if not content_text and settings.GROQ_API_KEY:
            try:
                content_text = await cls._generate_groq_fallback(
                    system_instruction, user_message, prompt, conversation_history
                )
            except Exception as e:
                logger.warning(f"Groq Agent synthesis fallback error: {e}")

        # 4. Fallback to Rule-Based Grounded Template
        if not content_text:
            content_text = cls._generate_deterministic_fallback(context, user_message, intent)

        # 5. Determine Next Action Recommendation
        if context.study_path:
            top_path = context.study_path[0]
            action_suggestion = {
                "action": "STUDY_CONCEPT",
                "concept_name": top_path.get("concept_name"),
                "priority": top_path.get("priority_score", 85.0),
                "reason": top_path.get("reason", "Recommended foundational topic")
            }

        return AgentChatMessage(
            role="assistant",
            content=content_text,
            intent=intent,
            citations=citations[:5],
            action_suggestion=action_suggestion
        )

    @classmethod
    def _build_synthesis_prompt(cls, ctx: LearnerContext, query: str, intent: AgentIntent) -> str:
        blocks = [f"Learner Target Roles: {', '.join(ctx.target_roles) if ctx.target_roles else 'General Technical Career'}"]

        if ctx.goals:
            blocks.append("Active Goals:\n" + "\n".join([f"- {g.get('title')} ({g.get('target_role', '')})" for g in ctx.goals]))

        if ctx.skills:
            blocks.append("Learner Concepts & Mastery:\n" + "\n".join([
                f"- {s['name']}: {round(s.get('mastery', 0))}% (Difficulty: {s.get('difficulty')}, Prerequisites: {', '.join(s.get('prerequisites', []))})"
                for s in ctx.skills[:8]
            ]))

        if ctx.misconceptions:
            blocks.append("Active Diagnoses:\n" + "\n".join([
                f"- {d.get('diagnosis_type')}: Target '{d.get('target_concept')}', Root Cause: '{d.get('suspected_root_concept')}' ({d.get('reason')})"
                for d in ctx.misconceptions[:3]
            ]))

        if ctx.grounded_chunks:
            blocks.append("Retrieved Source Material Grounding:\n" + "\n---\n".join([
                f"[{c.get('section', 'Chunk')}]: {c.get('text', '')}"
                for c in ctx.grounded_chunks[:5]
            ]))

        if ctx.web_knowledge:
            blocks.append("Current Industry Intelligence:\n" + "\n".join([
                f"- {w.get('topic')}: {w.get('standards')}"
                for w in ctx.web_knowledge
            ]))

        return "\n\n".join(blocks)

    @classmethod
    async def _generate_groq_fallback(
        cls,
        system_instruction: str,
        user_message: str,
        context_prompt: str,
        history: List[AgentChatMessage]
    ) -> str:
        messages = [{"role": "system", "content": system_instruction}]
        for m in history[-3:]:
            messages.append({"role": "user" if m.role == "user" else "assistant", "content": m.content})

        messages.append({
            "role": "user",
            "content": f"{user_message}\n\n[Context Grounding]:\n{context_prompt}"
        })

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.3
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
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
            return response.json()["choices"][0]["message"]["content"]
        raise Exception(f"Groq API returned {response.status_code}")

    @classmethod
    def _generate_deterministic_fallback(cls, ctx: LearnerContext, query: str, intent: AgentIntent) -> str:
        if intent == AgentIntent.CAREER_GUIDANCE:
            roles = ", ".join(ctx.target_roles) or "Software & AI Engineering"
            return (
                f"### Career Guidance: {roles}\n\n"
                "To accelerate your journey toward your target role:\n"
                "1. **Reinforce Core Prerequisites**: Ensure foundational topics achieve at least 75% mastery.\n"
                "2. **Address Diagnostic Weaknesses**: Review active misconceptions before attempting advanced projects.\n"
                "3. **Practical Implementation**: Build end-to-end applications demonstrating distributed systems or AI grounding."
            )
        elif intent == AgentIntent.STUDY_PLANNING:
            top_topic = ctx.study_path[0]["concept_name"] if ctx.study_path else "Foundational Concepts"
            return (
                "### Recommended Learning Plan for Today\n\n"
                f"🎯 **Primary Focus**: Review and practice **{top_topic}**\n\n"
                "1. Read the attached study material overview.\n"
                "2. Complete an adaptive MCQ assessment to verify retention.\n"
                "3. Review generated flashcards scheduled via spaced repetition."
            )
        else:
            return (
                f"I have reviewed your inquiry regarding **{query}**.\n\n"
                "Based on your current curriculum context, review the connected concepts in your Knowledge Graph "
                "or take a targeted assessment to calibrate your mastery score."
            )

def Math_round(val: Any) -> int:
    try:
        return round(float(val))
    except Exception:
        return 0
