import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.schemas.assistant import AssistantSourceItem, ConversationMessageSchema


class ConversationSession:
    """Represents an active multi-turn conversation session."""

    def __init__(self, conversation_id: str, project_id: int):
        self.conversation_id = conversation_id
        self.project_id = project_id
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.messages: List[Dict[str, Any]] = []
        self.last_entity: Optional[str] = None

    def add_user_message(self, content: str) -> str:
        msg_id = str(uuid.uuid4())
        self.updated_at = datetime.now(timezone.utc)
        self.messages.append({
            "id": msg_id,
            "role": "user",
            "content": content,
            "timestamp": self.updated_at.isoformat(),
            "sources": None,
            "suggested_questions": None,
        })
        # Keep last 16 messages (8 turns)
        if len(self.messages) > 16:
            self.messages = self.messages[-16:]
        return msg_id

    def add_assistant_message(
        self,
        content: str,
        sources: Optional[List[AssistantSourceItem]] = None,
        suggested_questions: Optional[List[str]] = None,
        referenced_entity: Optional[str] = None
    ) -> str:
        msg_id = str(uuid.uuid4())
        self.updated_at = datetime.now(timezone.utc)
        if referenced_entity:
            self.last_entity = referenced_entity
        self.messages.append({
            "id": msg_id,
            "role": "assistant",
            "content": content,
            "timestamp": self.updated_at.isoformat(),
            "sources": sources,
            "suggested_questions": suggested_questions,
        })
        if len(self.messages) > 16:
            self.messages = self.messages[-16:]
        return msg_id

    def get_messages_for_llm(self, limit: int = 6) -> List[Dict[str, str]]:
        """Returns the most recent user and assistant turns for the LLM prompt."""
        recent = self.messages[-limit:] if limit else self.messages
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def to_schema_messages(self) -> List[ConversationMessageSchema]:
        return [
            ConversationMessageSchema(
                id=m["id"],
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                sources=m.get("sources"),
                suggested_questions=m.get("suggested_questions")
            )
            for m in self.messages
        ]


class ConversationManager:
    """
    In-memory session manager for multi-turn assistant conversations.
    """

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, conversation_id: Optional[str], project_id: int) -> ConversationSession:
        if conversation_id and conversation_id in self._sessions:
            session = self._sessions[conversation_id]
            session.project_id = project_id
            return session

        cid = conversation_id or str(uuid.uuid4())
        session = ConversationSession(conversation_id=cid, project_id=project_id)
        self._sessions[cid] = session
        return session

    def get_session(self, conversation_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(conversation_id)

    def clear_session(self, conversation_id: str) -> bool:
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]
            return True
        return False


conversation_manager = ConversationManager()
