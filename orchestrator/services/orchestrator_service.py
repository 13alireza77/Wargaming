"""
High-level orchestrator: route -> unified LLM (single call) -> return.
Handles conversation persistence and errors. Uses one wargaming model for sub-60s responses.
"""
import logging
from typing import Dict, Any, List, Optional, Iterator

from .router import Router
from .unified_llm_service import StreamLLMError, UnifiedLLMService

logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(self):
        self.router = Router()

    def process_message(self, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process one user message: route for entities, single unified LLM call, optionally save conversation.
        Returns { success, reply, sources, conversation_id } or { success: False, error }.
        """
        try:
            # Resolve or create conversation
            conv_id = conversation_id
            conversation_context = []
            if conv_id:
                conversation_context = self._get_conversation_context(conv_id)
            else:
                conv_id = self._create_conversation()

            # Route (entity extraction only)
            intent = self.router.route(message)

            # Single unified LLM call
            unified = UnifiedLLMService()
            result = unified.analyze(
                message,
                conversation_context=conversation_context,
                intent=intent,
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Unified LLM failed"),
                }

            reply = result.get("reply", "")
            sources = result.get("sources", ["geography", "personnel", "weapons"])

            # Persist messages
            self._append_message(conv_id, "user", message)
            self._append_message(conv_id, "assistant", reply)

            return {
                "success": True,
                "reply": reply,
                "sources": sources,
                "conversation_id": conv_id,
            }
        except Exception as e:
            logger.exception("Orchestrator process_message failed")
            return {"success": False, "error": str(e)}

    def process_message_stream(
            self,
            message: str,
            conversation_id: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream one user message as SSE-style events:
        start -> token* -> done | error
        """
        try:
            conv_id = conversation_id
            conversation_context = []
            if conv_id:
                conversation_context = self._get_conversation_context(conv_id)
            else:
                conv_id = self._create_conversation()

            intent = self.router.route(message)
            unified = UnifiedLLMService()
            sources = ["geography", "personnel", "weapons"]
            reply_parts: List[str] = []

            yield {"event": "start", "conversation_id": conv_id}

            try:
                for chunk in unified.analyze_stream(
                    message,
                    conversation_context=conversation_context,
                    intent=intent,
                ):
                    reply_parts.append(chunk)
                    yield {"event": "token", "content": chunk}
            except StreamLLMError as e:
                yield {"event": "error", "error": str(e)}
                return

            reply = "".join(reply_parts)
            if not reply:
                reply = "I couldn't generate a response. Please try again."

            self._append_message(conv_id, "user", message)
            self._append_message(conv_id, "assistant", reply)

            yield {
                "event": "done",
                "conversation_id": conv_id,
                "sources": sources,
                "reply": reply,
            }
        except Exception as e:
            logger.exception("Orchestrator process_message_stream failed")
            yield {"event": "error", "error": str(e)}

    def _get_conversation_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

    def _create_conversation(self) -> str:
        try:
            from orchestrator.models import Conversation
            conv = Conversation.objects.create()
            return str(conv.id)
        except Exception:
            return self._get_conversation_id()

    def _get_conversation_context(self, conversation_id: str) -> List[Dict[str, str]]:
        try:
            from orchestrator.models import Conversation, Message
            conv = Conversation.objects.filter(id=conversation_id).first()
            if not conv:
                return []
            recent_messages = list(
                Message.objects.filter(conversation=conv).order_by('-created_at')[:10]
            )
            recent_messages.reverse()
            return [{'role': m.role, 'content': m.content or ''} for m in recent_messages]
        except Exception:
            return []

    def _append_message(self, conversation_id: str, role: str, content: str) -> None:
        try:
            from orchestrator.models import Conversation, Message
            conv = Conversation.objects.filter(id=conversation_id).first()
            if conv:
                Message.objects.create(conversation=conv, role=role, content=content)
        except Exception as e:
            logger.warning('Could not persist message: %s', e)
