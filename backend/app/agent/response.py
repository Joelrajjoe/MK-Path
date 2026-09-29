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

        # 2. Call Gemini Primary with multi-model fallback
        content_text = None
        gemini_keys = settings.GEMINI_API_KEYS or ([settings.GEMINI_API_KEY_RAW] if settings.GEMINI_API_KEY_RAW else [])
        gemini_models = [settings.GEMINI_MODEL, "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
        seen_models = set()
        model_candidates = [m for m in gemini_models if m and not (m in seen_models or seen_models.add(m))]

        # Format conversation history
        contents = []
        for msg in conversation_history[-4:]:
            role = "user" if msg.role == "user" else "model"
            contents.append(f"{role.upper()}: {msg.content}")

        contents.append(f"USER: {user_message}\n\n[CONTEXT DOSSIER]:\n{prompt}")
        prompt_payload = "\n\n".join(contents)

        for key in gemini_keys:
            if content_text:
                break
            client = genai.Client(api_key=key)
            for model_name in model_candidates:
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=model_name,
                            contents=prompt_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.4
                            )
                        ),
                        timeout=6.0
                    )
                    if response and response.text:
                        content_text = response.text
                        logger.info(f"Agent response generated via Gemini model: {model_name}")
                        break
                except Exception as e:
                    logger.warning(f"Gemini Agent synthesis error with model {model_name}: {e}")

        # 3. Fallback to Groq if Gemini fails
        if not content_text and settings.GROQ_API_KEY:
            for groq_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b"]:
                try:
                    content_text = await cls._generate_groq_fallback(
                        system_instruction, user_message, prompt, conversation_history, model=groq_model
                    )
                    if content_text:
                        logger.info(f"Agent response generated via Groq fallback ({groq_model})")
                        break
                except Exception as e:
                    logger.warning(f"Groq Agent synthesis fallback error with {groq_model}: {e}")

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
        history: List[AgentChatMessage],
        model: str = "qwen/qwen3.8-27b"
    ) -> str:
        messages = [{"role": "system", "content": system_instruction}]
        for m in history[-3:]:
            messages.append({"role": "user" if m.role == "user" else "assistant", "content": m.content})

        messages.append({
            "role": "user",
            "content": f"{user_message}\n\n[Context Grounding]:\n{context_prompt}"
        })

        payload = {
            "model": model,
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
            timeout=25
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        raise Exception(f"Groq API returned {response.status_code}: {response.text}")

    @classmethod
    def _generate_deterministic_fallback(cls, ctx: LearnerContext, query: str, intent: AgentIntent) -> str:
        roles = ", ".join(ctx.target_roles) if ctx.target_roles else "Software & AI Engineering"
        skills_summary = ", ".join([s["name"] for s in ctx.skills[:5]]) if ctx.skills else "Core programming & systems fundamentals"

        if intent in (AgentIntent.SKILL_GAP, AgentIntent.CAREER_GUIDANCE):
            return (
                f"### Strategic Career & Gap Analysis: {roles}\n\n"
                f"Based on your current learning profile and career target (**{roles}**):\n\n"
                f"**Current Assessed Skills:** {skills_summary}\n\n"
                "**Key Focus Areas & Next Steps:**\n"
                "1. **Strengthen Core Prerequisites**: Deepen mastery in distributed systems, asynchronous design, and API security to reach senior-level benchmarks (>85%).\n"
                "2. **Evidence-Driven Projects**: Build production-grade capstones featuring containerized services, caching layers, and high-throughput databases.\n"
                "3. **Targeted Calibration**: Head to the **Career Twin** or **Skill Gap** dashboard to run a verification assessment on missing competencies."
            )
        elif intent == AgentIntent.STUDY_PLANNING:
            top_topic = ctx.study_path[0]["concept_name"] if ctx.study_path else "Foundational Systems & Algorithms"
            return (
                "### Recommended Learning Action Plan\n\n"
                f"🎯 **Immediate Focus**: Deepen your mastery in **{top_topic}**\n\n"
                "1. **Read & Absorb**: Review connected lecture segments or study material.\n"
                "2. **Active Recall**: Test your intuition with an adaptive assessment.\n"
                "3. **Practical Implementation**: Implement a minimal working prototype to solidify your mental model."
            )
        else:
            return (
                f"### Guidance for: {query}\n\n"
                f"To help you advance toward **{roles}**:\n\n"
                f"1. **Analyze Your Active Concepts**: You are currently tracking **{skills_summary}**.\n"
                "2. **Calibrate Readiness**: Take a diagnostic quiz or explore the interactive Knowledge Graph to pinpoint prerequisite dependencies.\n"
                "3. **Ask the Concept Tutor**: For step-by-step Socratic deep-dives into specific technical algorithms, launch a session with the Concept Tutor."
            )

def Math_round(val: Any) -> int:
    try:
        return round(float(val))
    except Exception:
        return 0
