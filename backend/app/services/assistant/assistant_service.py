import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.models.project import Project
from app.models.architecture import ArchitectureAnalysis, GraphNode
from app.models.health import SoftwareHealthSnapshot
from app.models.risk import SoftwareRisk
from app.models.evolution import ChangeHotspot, TechnicalDebtIndicator
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantSourceItem,
    OllamaStatusResponse,
    ConversationHistoryResponse,
    SuggestedQuestionsResponse,
)
from app.services.assistant.ollama_service import (
    ollama_service,
    OllamaService,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaServiceError,
)
from app.services.assistant.context_engine import context_engine, ProjectContextEngine
from app.services.assistant.conversation_manager import conversation_manager, ConversationManager
from app.services.assistant.prompt_builder import prompt_builder, PromptBuilder

logger = logging.getLogger("digital_twin.assistant.service")


class AIProjectAssistantService:
    """
    Main orchestration service for the Phase 7 AI Project Assistant.
    Coordinates context retrieval, prompt construction, Ollama/Qwen generation,
    conversation state, and grounded source extraction.
    """

    def __init__(
        self,
        ollama: Optional[OllamaService] = None,
        context: Optional[ProjectContextEngine] = None,
        conv_mgr: Optional[ConversationManager] = None,
        prompter: Optional[PromptBuilder] = None,
    ):
        self.ollama = ollama or ollama_service
        self.context = context or context_engine
        self.conv_mgr = conv_mgr or conversation_manager
        self.prompter = prompter or prompt_builder

    def chat(
        self,
        project_id: int,
        message: str,
        db: Session,
        conversation_id: Optional[str] = None,
    ) -> AssistantChatResponse:
        """
        Processes a user question, retrieves relevant project intelligence,
        invokes Qwen via Ollama, and returns a grounded response.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # 1. Manage Conversation Session
        session = self.conv_mgr.get_or_create_session(conversation_id, project_id=project.id)
        cid = session.conversation_id
        session.add_user_message(message)

        # 2. Build Grounded Project Context
        prev_entity = session.last_entity
        context_payload = self.context.build_project_context(
            project_id=project.id,
            question=message,
            db=db,
            previous_entity=prev_entity
        )

        context_text = context_payload["context_text"]
        sources = context_payload["sources"]
        related_components = context_payload["related_components"]
        related_risks = context_payload["related_risks"]
        resolved_entity = context_payload.get("resolved_entity") or prev_entity

        # 3. Assemble Prompt with Conversation History
        history = session.get_messages_for_llm(limit=6)
        # Exclude the very last user message just added to history to avoid duplication in builder
        prior_turns = history[:-1] if history else []

        llm_messages = self.prompter.build_messages(
            question=message,
            project_context=context_text,
            conversation_history=prior_turns,
            is_general=context_payload.get("is_general", False)
        )

        # 4. Generate Answer via Ollama & Qwen
        try:
            answer = self.ollama.chat_completion(llm_messages)
            # Post-process to ensure no raw context blocks or internal system dumps were echoed
            answer = self._clean_llm_response(answer)
        except OllamaConnectionError:
            logger.warning(f"Ollama connection unavailable at {self.ollama.base_url}")
            answer = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="connection"
            )
        except OllamaModelNotFoundError:
            logger.warning(f"Configured Qwen model '{self.ollama.model}' not found in Ollama")
            answer = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="model_not_found"
            )
        except OllamaServiceError as exc:
            logger.error(f"Ollama service error: {exc}")
            answer = (
                f"The AI assistant encountered an issue with the local Qwen model: {exc.message}\n\n"
                f"Please verify that Ollama is healthy at `{self.ollama.base_url}`."
            )

        # 5. Generate Contextual Follow-Up Questions
        follow_ups = self._generate_follow_up_questions(
            question=message,
            entity=resolved_entity,
            related_components=related_components,
            related_risks=related_risks,
            intent=context_payload.get("intent", "general")
        )

        # 6. Extract Recommendations
        recommendations = self._extract_recommendations(answer, related_risks)

        # 7. Persist Assistant Turn in Session
        session.add_assistant_message(
            content=answer,
            sources=sources,
            suggested_questions=follow_ups,
            referenced_entity=resolved_entity
        )

        return AssistantChatResponse(
            answer=answer,
            conversation_id=cid,
            sources=sources,
            related_components=related_components,
            related_risks=related_risks,
            recommendations=recommendations,
            suggested_questions=follow_ups,
        )

    async def chat_stream(
        self,
        project_id: int,
        message: str,
        db: Session,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processes a user question, retrieves grounded repository intelligence,
        streams tokens in real-time from Qwen via Ollama, and yields structured SSE events.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            yield {"event": "error", "error": f"Project with ID {project_id} not found."}
            return

        # 1. Manage Conversation Session
        session = self.conv_mgr.get_or_create_session(conversation_id, project_id=project.id)
        cid = session.conversation_id
        session.add_user_message(message)

        yield {"event": "start", "conversation_id": cid}

        # 2. Build Grounded Project Context
        prev_entity = session.last_entity
        context_payload = self.context.build_project_context(
            project_id=project.id,
            question=message,
            db=db,
            previous_entity=prev_entity
        )

        context_text = context_payload["context_text"]
        sources = context_payload["sources"]
        related_components = context_payload["related_components"]
        related_risks = context_payload["related_risks"]
        resolved_entity = context_payload.get("resolved_entity") or prev_entity
        serialized_sources = [
            s.model_dump() if hasattr(s, "model_dump") else s.dict()
            for s in sources
        ]

        # Immediately yield sources & context metadata so frontend can render references drawer
        yield {
            "event": "sources",
            "sources": serialized_sources,
            "related_components": related_components,
            "related_risks": related_risks,
            "resolved_entity": resolved_entity,
            "intent": context_payload.get("intent", "general"),
        }

        # 3. Assemble Prompt with Conversation History
        history = session.get_messages_for_llm(limit=6)
        prior_turns = history[:-1] if history else []

        llm_messages = self.prompter.build_messages(
            question=message,
            project_context=context_text,
            conversation_history=prior_turns,
            is_general=context_payload.get("is_general", False)
        )

        # 4. Stream Answer from Ollama & Qwen
        full_tokens: List[str] = []
        is_fallback = False

        try:
            async for token in self.ollama.chat_stream(llm_messages):
                full_tokens.append(token)
                yield {"event": "token", "token": token}
        except OllamaConnectionError:
            logger.warning(f"Ollama connection unavailable at {self.ollama.base_url}")
            is_fallback = True
            fallback = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="connection"
            )
            full_tokens.append(fallback)
            yield {"event": "token", "token": fallback}
        except OllamaModelNotFoundError:
            logger.warning(f"Configured Qwen model '{self.ollama.model}' not found in Ollama")
            is_fallback = True
            fallback = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="model_not_found"
            )
            full_tokens.append(fallback)
            yield {"event": "token", "token": fallback}
        except OllamaTimeoutError:
            logger.warning("Ollama token generation timed out")
            is_fallback = True
            fallback = "\n\n> **Notice:** The request timed out while generating a response. You may retry or ask a more specific question."
            full_tokens.append(fallback)
            yield {"event": "token", "token": fallback}
        except Exception as exc:
            logger.error(f"Error during assistant stream generation: {exc}")
            is_fallback = True
            fallback = f"\n\n> **Error:** {str(exc)}"
            full_tokens.append(fallback)
            yield {"event": "token", "token": fallback}

        full_answer = "".join(full_tokens)
        if not is_fallback:
            full_answer = self._clean_llm_response(full_answer)

        # 5. Generate Contextual Follow-Up Questions
        follow_ups = self._generate_follow_up_questions(
            question=message,
            entity=resolved_entity,
            related_components=related_components,
            related_risks=related_risks,
            intent=context_payload.get("intent", "general")
        )

        # 6. Extract Recommendations
        recommendations = self._extract_recommendations(full_answer, related_risks)

        # 7. Persist Assistant Turn in Session
        session.add_assistant_message(
            content=full_answer,
            sources=sources,
            suggested_questions=follow_ups,
            referenced_entity=resolved_entity
        )

        # 8. Complete Event
        yield {
            "event": "done",
            "conversation_id": cid,
            "answer": full_answer,
            "suggested_questions": follow_ups,
            "recommendations": recommendations,
        }

    def get_suggested_questions(self, project_id: int, db: Session) -> SuggestedQuestionsResponse:
        """
        Generates contextual prompt suggestions based on actual project telemetry.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return SuggestedQuestionsResponse(project_id=project_id, project_name="Unknown", questions=[])

        questions = [
            f"Explain the architecture and main modules of {project.name}.",
            "What are the highest-risk components in this repository?",
            "What is the overall software health score and what factors drive it?",
            "What are the most active code change hotspots?",
        ]

        # Check if project has detected circular dependencies
        analysis = db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project_id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(desc(ArchitectureAnalysis.analyzed_at)).first()

        if analysis and analysis.cycles and len(analysis.cycles) > 0:
            questions.insert(1, f"Are there any circular dependencies detected in {project.name}?")

        # Check if there are active critical risks
        crit_risks = db.query(SoftwareRisk).filter(
            SoftwareRisk.project_id == project_id,
            SoftwareRisk.severity.in_(["HIGH", "CRITICAL"]),
            SoftwareRisk.status.in_(["OPEN", "ACKNOWLEDGED"])
        ).first()

        if crit_risks:
            questions.append(f"Why is {crit_risks.title} flagged as a critical risk?")

        return SuggestedQuestionsResponse(
            project_id=project_id,
            project_name=project.name,
            questions=questions[:5]
        )

    def get_conversation_history(self, conversation_id: str, project_id: int) -> ConversationHistoryResponse:
        session = self.conv_mgr.get_session(conversation_id)
        if not session:
            return ConversationHistoryResponse(
                conversation_id=conversation_id,
                project_id=project_id,
                messages=[]
            )
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            project_id=project_id,
            messages=session.to_schema_messages()
        )

    def clear_conversation(self, conversation_id: str) -> bool:
        return self.conv_mgr.clear_session(conversation_id)

    def get_status(self) -> OllamaStatusResponse:
        health = self.ollama.check_health()
        return OllamaStatusResponse(
            connected=health["connected"],
            base_url=health["base_url"],
            model=health["model"],
            model_available=health["model_available"],
            available_models=health["available_models"],
            error=health["error"]
        )

    def _clean_llm_response(self, text: str) -> str:
        """Strips accidental prompt echoes or system headers from Qwen's output."""
        cleaned = text.strip()
        # Remove any internal context banners if echoed
        if "=== VERIFIED REPOSITORY EVIDENCE" in cleaned:
            parts = cleaned.split("============================================================================")
            cleaned = parts[-1].strip()
        if "User Question:" in cleaned and "\n\n" in cleaned:
            cleaned = cleaned.split("User Question:")[-1]
            if "\n\n" in cleaned:
                cleaned = cleaned.split("\n\n", 1)[-1].strip()
        return cleaned

    def _generate_offline_fallback(
        self,
        question: str,
        project: Project,
        context_payload: Dict[str, Any],
        error_type: str
    ) -> str:
        """
        Gracefully handles Ollama connection failures by informing the user on how
        to start Ollama and providing a structured, grounded synthesis from repository telemetry.
        """
        model_name = self.ollama.model
        base_url = self.ollama.base_url

        if error_type == "connection":
            notice = (
                f"> **Notice:** I couldn't connect to the local Qwen model at `{base_url}`. "
                f"Make sure Ollama is running (`ollama serve`) and the configured model is available.\n\n"
            )
        else:
            notice = (
                f"> **Notice:** The configured model `{model_name}` is not currently installed in Ollama. "
                f"Run `ollama pull {model_name}` to download it.\n\n"
            )

        intent = context_payload.get("intent", "general")
        resolved = context_payload.get("resolved_entity")

        lines = [notice]
        lines.append(f"Here is the verified telemetry from the repository analysis for **{project.full_name}**:\n")

        if resolved:
            lines.append(f"### Component: `{resolved}`\n")
            lines.append(f"The project analysis was searched for `{resolved}`.")
            if context_payload.get("related_components"):
                comps = ", ".join([f"`{c}`" for c in context_payload["related_components"][:5]])
                lines.append(f"- **Direct relationships / components:** {comps}")

        # Software Health
        if project.health_score is not None:
            lines.append(f"- **Overall Health Score:** {project.health_score:.1f}/100")

        # Active Risks
        risks = context_payload.get("related_risks", [])
        if risks:
            lines.append("\n**Active Risks Identified:**")
            for r in risks[:3]:
                lines.append(f"- {r}")

        lines.append(f"\nOnce Ollama is running with `{model_name}`, natural conversational responses with full technical reasoning will be enabled.")
        return "\n".join(lines)

    def _generate_follow_up_questions(
        self,
        question: str,
        entity: Optional[str],
        related_components: List[str],
        related_risks: List[str],
        intent: str
    ) -> List[str]:
        """Generates 2–4 natural follow-up questions tailored to the current context."""
        follow_ups = []

        if entity:
            follow_ups.append(f"What components depend directly on {entity}?")
            follow_ups.append(f"Are there any risks or technical debt associated with {entity}?")
            follow_ups.append(f"Where is {entity} implemented in the file tree?")
        elif intent == "architecture":
            follow_ups.append("Which modules have the highest coupling?")
            follow_ups.append("Are there any circular dependencies?")
            follow_ups.append("What are the main architectural hotspots?")
        elif intent == "risks":
            follow_ups.append("What should be remediated first?")
            follow_ups.append("How does this impact the overall health score?")
            follow_ups.append("Which components are affected by these risks?")
        elif intent == "health":
            follow_ups.append("Which health dimensions have degraded scores?")
            follow_ups.append("What are the biggest risks currently tracked?")
            follow_ups.append("What are the recommended fixes to improve the score?")
        else:
            if related_components:
                follow_ups.append(f"Tell me more about {related_components[0]}.")
            follow_ups.append("Explain the project architecture.")
            follow_ups.append("What are the most active code hotspots?")

        # Deduplicate and return top 3
        seen = set()
        unique = []
        for f in follow_ups:
            if f.lower() not in seen and f.lower() != question.strip().lower():
                seen.add(f.lower())
                unique.append(f)
        return unique[:3]

    def _extract_recommendations(self, answer: str, related_risks: List[str]) -> List[str]:
        """Extracts concise recommendations from answer or active risks."""
        recs = []
        if related_risks:
            recs.append(f"Review and mitigate active risk: {related_risks[0]}")
        # Look for bullet points with 'recommend', 'should', 'consider'
        for line in answer.splitlines():
            line_str = line.strip(" -*0123456789.")
            if any(k in line_str.lower() for k in ["recommend", "consider", "should", "suggest"]):
                if len(line_str) > 15 and len(line_str) < 160:
                    recs.append(line_str)
                    if len(recs) >= 3:
                        break
        return recs[:3]


assistant_service = AIProjectAssistantService()
