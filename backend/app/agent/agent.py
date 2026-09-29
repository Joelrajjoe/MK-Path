"""
MK-Path 2.0 Personal AI Learning & Career Agent
Main orchestrator unifying Intent Routing, Context Building, and Grounded Response Generation.
"""
import logging
from typing import Dict, Any, List, Optional
from .models import (
    AgentIntent, AgentChatRequest, AgentChatResponse,
    AgentChatMessage, AgentConversation, SourceCitation
)
from .router import IntentRouter
from .context_builder import ContextBuilder
from .response import AgentResponseEngine
from .. import crud

logger = logging.getLogger("mkpath.agent")

class PersonalLearningAgent:
    """
    Central AI Learning & Career Agent for MK-Path 2.0.
    """

    @classmethod
    async def chat(
        cls,
        db: Any,
        clerk_user_id: str,
        request: AgentChatRequest
    ) -> AgentChatResponse:
        """
        Orchestrates full cycle: intent routing, context building, response synthesis, and conversation persistence.
        """
        # 1. Resolve or Create Conversation
        conversation = None
        if request.conversation_id:
            conv_doc = await crud.get_agent_conversation(db, request.conversation_id, clerk_user_id)
            if conv_doc:
                conversation = conv_doc

        if not conversation:
            # Create new conversation
            conv_title = request.message[:40] + "..." if len(request.message) > 40 else request.message
            conversation = {
                "clerk_user_id": clerk_user_id,
                "title": conv_title,
                "messages": [],
                "active_intent": AgentIntent.GENERAL.value,
                "created_at": datetime_utcnow(),
                "updated_at": datetime_utcnow()
            }
            conv_record = await crud.create_agent_conversation(db, conversation)
            conversation["_id"] = str(conv_record["_id"])

        conversation_id_str = str(conversation.get("_id") or conversation.get("id"))

        # 2. Intent Routing
        context_hints = {
            "focus_concept": request.context_focus_concept,
            "material_id": request.context_material_id
        }
        intent = request.override_intent or IntentRouter.route_intent(request.message, context_hints)

        # 3. Context Assembling
        context = await ContextBuilder.build_context(
            db=db,
            clerk_user_id=clerk_user_id,
            query=request.message,
            intent=intent,
            focus_concept=request.context_focus_concept,
            material_id=request.context_material_id,
            include_web=request.include_web_search
        )

        # 4. Synthesize Response
        history_msgs = [
            AgentChatMessage(**m) for m in conversation.get("messages", [])
        ]
        
        user_msg = AgentChatMessage(
            role="user",
            content=request.message,
            intent=intent,
            timestamp=datetime_utcnow()
        )

        assistant_msg = await AgentResponseEngine.generate_response(
            context=context,
            conversation_history=history_msgs,
            user_message=request.message,
            intent=intent
        )

        # 5. Persist to MongoDB
        await crud.append_agent_conversation_message(
            db, conversation_id_str, clerk_user_id, user_msg.model_dump()
        )
        await crud.append_agent_conversation_message(
            db, conversation_id_str, clerk_user_id, assistant_msg.model_dump()
        )

        return AgentChatResponse(
            conversation_id=conversation_id_str,
            message=assistant_msg,
            intent_detected=intent,
            sources_used=assistant_msg.citations,
            recommended_next_action=assistant_msg.action_suggestion
        )

def datetime_utcnow():
    from datetime import datetime
    return datetime.utcnow()
