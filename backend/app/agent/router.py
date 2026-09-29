"""
MK-Path 2.0 Intent Router
Decides user query intent and context retrieval strategy.
"""
import re
import logging
from typing import Dict, Any, List
from .models import AgentIntent

logger = logging.getLogger("mkpath.agent.router")

class IntentRouter:
    """
    Deterministic & Heuristic Intent Classification Engine
    Routes query into 11 distinct learner intelligence intents.
    """

    INTENT_PATTERNS = {
        AgentIntent.DOCUMENT_QA: [
            r"\b(in my notes|in the pdf|in my uploaded material|according to the document|from my file|in the lecture|in chapter|page \d+)\b",
            r"\b(where does the author|what does the document say|find in material)\b"
        ],
        AgentIntent.INTERVIEW_PREPARATION: [
            r"\b(mock interview|interview question|interview questions|technical interview|system design interview|coding interview|behavioral question|screen test|quiz me for an interview|interview for|prepare for an interview|interview preparation)\b",
            r"\b(how would you answer|interview prep)\b"
        ],
        AgentIntent.SKILL_GAP: [
            r"\b(skill gap|skill gaps|what am i missing|my gaps|why am i weak|where do i lack|gap analysis)\b",
            r"\b(am i ready for|my readiness for)\b"
        ],
        AgentIntent.PROJECT_GUIDANCE: [
            r"\b(project idea|project ideas|build a project|capstone|portfolio project|architecture design|implementation steps|how to build|code structure|tech stack for)\b"
        ],
        AgentIntent.CURRENT_INDUSTRY: [
            r"\b(recently|latest|current trend|in 2024|in 2025|in 2026|new in|what changed in|langgraph|langchain|gemini 2|deepseek|claude 3|llama 3|state of the art|sota)\b",
            r"\b(industry standards today|modern practices in|updates to)\b"
        ],
        AgentIntent.CAREER_GUIDANCE: [
            r"\b(career|job|role|salary|hiring|become a|path to become|backend engineer|data scientist|ml engineer|frontend developer|cloud architect|devops)\b",
            r"\b(industry expectations|job market|portfolio|resume|transition to)\b"
        ],
        AgentIntent.STUDY_PLANNING: [
            r"\b(what should i study|study plan|study today|learning path|schedule for today|what next|where to start|daily target|roadmap)\b"
        ],
        AgentIntent.RESOURCE_SEARCH: [
            r"\b(recommend resource|find resources|resources for|book|tutorial|youtube video|documentation link|devdocs|course|article|where can i read more)\b"
        ],
        AgentIntent.CONCEPT_TUTOR: [
            r"\b(socratic|quiz me on|quiz me|test my understanding|ask me a question|teach me|guide me through|step by step inquiry)\b"
        ],
        AgentIntent.LEARNING_EXPLANATION: [
            r"\b(explain|what is|how does|why does|difference between|intuition behind|define|break down|analogy for|help me understand)\b"
        ],
    }

    @classmethod
    def route_intent(cls, message: str, context_hints: Dict[str, Any] = None) -> AgentIntent:
        """
        Classifies incoming message into appropriate AgentIntent.
        """
        text = message.lower().strip()

        # Check explicit patterns
        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(f"Intent classified as {intent.value} via pattern: {pattern}")
                    return intent

        # Context-based routing hints
        if context_hints:
            if context_hints.get("focus_concept"):
                return AgentIntent.LEARNING_EXPLANATION
            if context_hints.get("material_id"):
                return AgentIntent.DOCUMENT_QA

        # Default fallback: check if it's an educational/inquiry question vs general conversation
        greeting_patterns = r"\b(hello|hi|hey|good morning|good evening|who are you|how can you help|what can you do|thanks|thank you)\b"
        if re.search(greeting_patterns, text, re.IGNORECASE):
            return AgentIntent.GENERAL

        if len(text.split()) > 3 and any(w in text for w in ["what", "how", "why", "who", "when", "can"]):
            return AgentIntent.LEARNING_EXPLANATION

        return AgentIntent.GENERAL

    def route(self, message: str, context_hints: Dict[str, Any] = None) -> AgentIntent:
        """Instance alias for route_intent."""
        return self.route_intent(message, context_hints)

    def get_context_requirements(self, intent: AgentIntent) -> List[str]:
        """Returns list of active context requirements for the intent."""
        sources = self.get_required_context_sources(intent)
        return [k for k, v in sources.items() if v]

    @classmethod
    def get_required_context_sources(cls, intent: AgentIntent) -> Dict[str, bool]:
        """
        Determines which database & external context sources need to be queried for this intent.
        """
        config = {
            "load_learner_profile": True,
            "load_goals": False,
            "load_mastery": False,
            "load_misconceptions": False,
            "load_study_path": False,
            "load_materials_rag": False,
            "load_youtube_rag": False,
            "load_web_knowledge": False,
            "load_assignments": False,
            "load_knowledge_graph": False
        }

        if intent == AgentIntent.DOCUMENT_QA:
            config["load_materials_rag"] = True
            config["load_youtube_rag"] = True
            config["load_knowledge_graph"] = True

        elif intent == AgentIntent.LEARNING_EXPLANATION:
            config["load_mastery"] = True
            config["load_misconceptions"] = True
            config["load_materials_rag"] = True
            config["load_knowledge_graph"] = True

        elif intent == AgentIntent.CONCEPT_TUTOR:
            config["load_mastery"] = True
            config["load_misconceptions"] = True
            config["load_materials_rag"] = True
            config["load_knowledge_graph"] = True

        elif intent in (AgentIntent.CAREER_GUIDANCE, AgentIntent.SKILL_GAP):
            config["load_goals"] = True
            config["load_mastery"] = True
            config["load_knowledge_graph"] = True
            config["load_web_knowledge"] = True

        elif intent == AgentIntent.CURRENT_INDUSTRY:
            config["load_goals"] = True
            config["load_web_knowledge"] = True

        elif intent == AgentIntent.PROJECT_GUIDANCE:
            config["load_goals"] = True
            config["load_mastery"] = True
            config["load_materials_rag"] = True

        elif intent == AgentIntent.INTERVIEW_PREPARATION:
            config["load_goals"] = True
            config["load_mastery"] = True
            config["load_misconceptions"] = True
            config["load_web_knowledge"] = True

        elif intent == AgentIntent.STUDY_PLANNING:
            config["load_goals"] = True
            config["load_mastery"] = True
            config["load_misconceptions"] = True
            config["load_study_path"] = True
            config["load_assignments"] = True

        elif intent == AgentIntent.RESOURCE_SEARCH:
            config["load_mastery"] = True
            config["load_misconceptions"] = True
            config["load_web_knowledge"] = True

        else: # GENERAL
            config["load_goals"] = True
            config["load_mastery"] = True

        return config
