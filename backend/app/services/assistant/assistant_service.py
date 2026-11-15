import time
import logging
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
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
    XAIExplanation,
)
from app.services.assistant.ollama_service import (
    ollama_service,
    OllamaService,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaServiceError,
)
from app.services.assistant.groq_service import (
    groq_service,
    GroqService,
    GroqConnectionError,
    GroqAuthError,
    GroqRateLimitError,
    GroqModelNotFoundError,
    GroqTimeoutError,
    GroqServiceError,
)
from app.services.assistant.context_engine import context_engine, ProjectContextEngine
from app.services.assistant.conversation_manager import conversation_manager, ConversationManager
from app.services.assistant.prompt_builder import prompt_builder, PromptBuilder

logger = logging.getLogger("digital_twin.assistant.service")


class AIProjectAssistantService:
    """
    Main orchestration service for the Phase 7 AI Project Assistant.
    Coordinates context retrieval, prompt construction, Groq LPU / Ollama generation,
    conversation state, and grounded source extraction.
    """

    def __init__(
        self,
        ollama: Optional[OllamaService] = None,
        groq: Optional[GroqService] = None,
        context: Optional[ProjectContextEngine] = None,
        conv_mgr: Optional[ConversationManager] = None,
        prompter: Optional[PromptBuilder] = None,
        provider: Optional[str] = None,
    ):
        self.ollama = ollama or ollama_service
        self.groq = groq or groq_service
        self.context = context or context_engine
        self.conv_mgr = conv_mgr or conversation_manager
        self.prompter = prompter or prompt_builder

        # Provider mode can be "auto", "groq", or "ollama"
        raw_mode = (provider or getattr(settings, "AI_PROVIDER", "auto") or "auto").lower()
        self._provider_mode = raw_mode if raw_mode in ("auto", "groq", "ollama") else "auto"
        self._provider = self._provider_mode

        # In-memory answer cache for fast sub-second repeated queries
        self._answer_cache: Dict[str, Tuple[float, AssistantChatResponse]] = {}
        self._cache_ttl = float(getattr(settings, "AI_CACHE_TTL_SECONDS", 120))

    @property
    def provider(self) -> str:
        return getattr(self, "_provider", None) or self._provider_mode

    @property
    def provider_mode(self) -> str:
        return getattr(self, "_provider", None) or self._provider_mode

    def set_provider_mode(self, mode: str) -> str:
        cleaned = mode.strip().lower()
        if cleaned in ("auto", "groq", "ollama"):
            self._provider_mode = cleaned
            self._provider = cleaned
            logger.info(f"AI Assistant provider mode switched to: {cleaned}")
            return cleaned
        raise ValueError(f"Invalid provider mode '{mode}'. Choose 'auto', 'groq', or 'ollama'.")

    def _determine_active_and_fallback_provider(self) -> Tuple[str, Optional[str]]:
        """
        Dynamically probes provider status and returns (primary_provider, fallback_provider).
        Supports 'auto', 'groq', and 'ollama' modes cleanly.
        """
        groq_ready = bool(self.groq.api_key)
        ollama_health = self.ollama.check_health()
        ollama_ready = ollama_health.get("connected", False) and ollama_health.get("model_available", False)

        if self._provider_mode == "groq":
            return ("groq", "ollama" if ollama_ready else None)
        elif self._provider_mode == "ollama":
            return ("ollama", "groq" if groq_ready else None)
        else:  # auto
            if groq_ready:
                return ("groq", "ollama" if ollama_ready else None)
            elif ollama_ready:
                return ("ollama", None)
            else:
                return ("deterministic", None)

    def chat(
        self,
        project_id: int,
        message: str,
        db: Session,
        conversation_id: Optional[str] = None,
    ) -> AssistantChatResponse:
        """
        Processes a user question, retrieves relevant project intelligence,
        invokes Groq or Ollama dynamically with automatic fallback,
        and returns a grounded response with Explainable AI (XAI) metadata.
        """
        # 0. Check in-memory answer cache for rapid sub-second responses
        cache_key = f"{project_id}:{message.strip().lower()}:{self._provider_mode}"
        now_ts = time.time()
        if cache_key in self._answer_cache:
            saved_time, cached_resp = self._answer_cache[cache_key]
            if now_ts - saved_time < self._cache_ttl:
                return cached_resp.model_copy(update={"is_cached": True})

        start_time = time.perf_counter()

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

        # 3. Assemble Prompt with Conversation History and Anti-Hallucination Guard
        history = session.get_messages_for_llm(limit=6)
        prior_turns = history[:-1] if history else []

        llm_messages = self.prompter.build_messages(
            question=message,
            project_context=context_text,
            conversation_history=prior_turns,
            is_general=context_payload.get("is_general", False)
        )

        # 4. Determine Primary & Fallback Providers
        primary, fallback = self._determine_active_and_fallback_provider()
        actual_provider = primary
        answer = None

        if primary == "groq":
            try:
                answer = self.groq.chat_completion(llm_messages)
                answer = self._clean_llm_response(answer)
            except Exception as exc:
                logger.warning(f"Groq API primary unavailable ({exc}), attempting fallback to {fallback}...")
                if fallback == "ollama":
                    try:
                        answer = self.ollama.chat_completion(llm_messages)
                        answer = self._clean_llm_response(answer)
                        actual_provider = "ollama (fallback)"
                    except Exception as ollama_exc:
                        logger.warning(f"Ollama fallback also failed: {ollama_exc}")
                        answer = self._generate_offline_fallback(
                            question=message,
                            project=project,
                            context_payload=context_payload,
                            error_type="groq_error",
                            custom_error=str(exc)
                        )
                        actual_provider = "deterministic (fallback)"
                else:
                    answer = self._generate_offline_fallback(
                        question=message,
                        project=project,
                        context_payload=context_payload,
                        error_type="groq_error",
                        custom_error=str(exc)
                    )
                    actual_provider = "deterministic (fallback)"

        elif primary == "ollama":
            try:
                answer = self.ollama.chat_completion(llm_messages)
                answer = self._clean_llm_response(answer)
            except Exception as exc:
                logger.warning(f"Ollama primary unavailable ({exc}), attempting fallback to {fallback}...")
                if fallback == "groq":
                    try:
                        answer = self.groq.chat_completion(llm_messages)
                        answer = self._clean_llm_response(answer)
                        actual_provider = "groq (fallback)"
                    except Exception as groq_exc:
                        logger.warning(f"Groq fallback also failed: {groq_exc}")
                        answer = self._generate_offline_fallback(
                            question=message,
                            project=project,
                            context_payload=context_payload,
                            error_type="connection"
                        )
                        actual_provider = "deterministic (fallback)"
                else:
                    answer = self._generate_offline_fallback(
                        question=message,
                        project=project,
                        context_payload=context_payload,
                        error_type="connection"
                    )
                    actual_provider = "deterministic (fallback)"

        else:
            # Deterministic fallback mode
            answer = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="offline"
            )
            actual_provider = "deterministic"

        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

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

        # 7. Generate Explainable AI (XAI) Attribution
        xai_data = self.context.generate_xai_metadata(project, context_payload, answer, db)
        xai_explanation = XAIExplanation(**xai_data)

        # 8. Persist Assistant Turn in Session
        session.add_assistant_message(
            content=answer,
            sources=sources,
            suggested_questions=follow_ups,
            referenced_entity=resolved_entity
        )

        response = AssistantChatResponse(
            answer=answer,
            conversation_id=cid,
            provider=actual_provider,
            provider_mode=self._provider_mode,
            latency_ms=latency_ms,
            is_cached=False,
            sources=sources,
            related_components=related_components,
            related_risks=related_risks,
            recommendations=recommendations,
            suggested_questions=follow_ups,
            xai_explanation=xai_explanation,
        )

        # Save in cache
        self._answer_cache[cache_key] = (now_ts, response)
        return response

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

        start_time = time.perf_counter()
        primary, fallback = self._determine_active_and_fallback_provider()
        actual_provider = primary

        yield {
            "event": "start",
            "conversation_id": cid,
            "provider": primary,
            "provider_mode": self._provider_mode
        }

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

        # 4. Stream Answer with dynamic primary & fallback
        full_tokens: List[str] = []
        is_fallback = False
        streamed_ok = False

        if primary == "groq":
            try:
                async for token in self.groq.chat_stream(llm_messages):
                    full_tokens.append(token)
                    yield {"event": "token", "token": token}
                streamed_ok = True
            except Exception as exc:
                logger.warning(f"Groq streaming unavailable ({exc}), attempting fallback to {fallback}...")
                if not full_tokens and fallback == "ollama":
                    try:
                        actual_provider = "ollama (fallback)"
                        async for token in self.ollama.chat_stream(llm_messages):
                            full_tokens.append(token)
                            yield {"event": "token", "token": token}
                        streamed_ok = True
                    except Exception as ollama_exc:
                        logger.warning(f"Ollama fallback stream also failed: {ollama_exc}")
                        is_fallback = True
                        actual_provider = "deterministic (fallback)"
                        fb_text = self._generate_offline_fallback(
                            question=message,
                            project=project,
                            context_payload=context_payload,
                            error_type="groq_error",
                            custom_error=str(exc)
                        )
                        full_tokens.append(fb_text)
                        yield {"event": "token", "token": fb_text}
                else:
                    is_fallback = True
                    actual_provider = "deterministic (fallback)"
                    fb_text = self._generate_offline_fallback(
                        question=message,
                        project=project,
                        context_payload=context_payload,
                        error_type="groq_error",
                        custom_error=str(exc)
                    )
                    full_tokens.append(fb_text)
                    yield {"event": "token", "token": fb_text}

        elif primary == "ollama":
            try:
                async for token in self.ollama.chat_stream(llm_messages):
                    full_tokens.append(token)
                    yield {"event": "token", "token": token}
                streamed_ok = True
            except Exception as exc:
                logger.warning(f"Ollama streaming unavailable ({exc}), attempting fallback to {fallback}...")
                if not full_tokens and fallback == "groq":
                    try:
                        actual_provider = "groq (fallback)"
                        async for token in self.groq.chat_stream(llm_messages):
                            full_tokens.append(token)
                            yield {"event": "token", "token": token}
                        streamed_ok = True
                    except Exception as groq_exc:
                        logger.warning(f"Groq fallback stream also failed: {groq_exc}")
                        is_fallback = True
                        actual_provider = "deterministic (fallback)"
                        fb_text = self._generate_offline_fallback(
                            question=message,
                            project=project,
                            context_payload=context_payload,
                            error_type="connection"
                        )
                        full_tokens.append(fb_text)
                        yield {"event": "token", "token": fb_text}
                else:
                    is_fallback = True
                    actual_provider = "deterministic (fallback)"
                    fb_text = self._generate_offline_fallback(
                        question=message,
                        project=project,
                        context_payload=context_payload,
                        error_type="connection"
                    )
                    full_tokens.append(fb_text)
                    yield {"event": "token", "token": fb_text}

        else:
            # Deterministic offline synthesis
            is_fallback = True
            actual_provider = "deterministic"
            fb_text = self._generate_offline_fallback(
                question=message,
                project=project,
                context_payload=context_payload,
                error_type="offline"
            )
            full_tokens.append(fb_text)
            yield {"event": "token", "token": fb_text}

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

        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

        # 7. Generate Explainable AI (XAI) Attribution
        xai_data = self.context.generate_xai_metadata(project, context_payload, full_answer, db)

        # 8. Persist Assistant Turn in Session
        session.add_assistant_message(
            content=full_answer,
            sources=sources,
            suggested_questions=follow_ups,
            referenced_entity=resolved_entity
        )

        # 9. Complete Event
        yield {
            "event": "done",
            "conversation_id": cid,
            "answer": full_answer,
            "provider": actual_provider,
            "provider_mode": self._provider_mode,
            "latency_ms": latency_ms,
            "suggested_questions": follow_ups,
            "recommendations": recommendations,
            "xai_explanation": xai_data,
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
        groq_health = self.groq.check_health()
        ollama_health = self.ollama.check_health()
        groq_ok = groq_health.get("connected", False) and groq_health.get("model_available", False)
        ollama_ok = ollama_health.get("connected", False) and ollama_health.get("model_available", False)

        mode = self._provider_mode
        if mode == "groq":
            active = "groq"
            is_conn = groq_ok
            base_url = groq_health.get("base_url", "https://api.groq.com")
            model = groq_health.get("model", getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b"))
            models = groq_health.get("available_models", [])
            err = groq_health.get("error")
        elif mode == "ollama":
            active = "ollama"
            is_conn = ollama_ok
            base_url = ollama_health.get("base_url", getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"))
            model = ollama_health.get("model", getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b"))
            models = ollama_health.get("available_models", [])
            err = ollama_health.get("error")
        else:  # auto
            if groq_ok:
                active = "groq"
                is_conn = True
                base_url = groq_health.get("base_url", "https://api.groq.com")
                model = groq_health.get("model", getattr(settings, "GROQ_MODEL", "qwen/qwen3.8-27b"))
                models = groq_health.get("available_models", [])
                err = None
            elif ollama_ok:
                active = "ollama"
                is_conn = True
                base_url = ollama_health.get("base_url", getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"))
                model = ollama_health.get("model", getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b"))
                models = ollama_health.get("available_models", [])
                err = f"Groq not configured ({groq_health.get('error')}). Using local Ollama." if groq_health.get("error") else None
            else:
                active = "deterministic"
                is_conn = False
                base_url = "deterministic://offline-grounded"
                model = "rule-based-xai"
                models = []
                err = "No LLM provider available. Operating in grounded deterministic XAI synthesis mode."

        return OllamaStatusResponse(
            connected=is_conn,
            base_url=base_url,
            model=model,
            model_available=is_conn,
            available_models=models,
            error=err,
            provider=active,
            provider_mode=mode,
            groq_available=groq_ok,
            ollama_available=ollama_ok,
            active_provider=active,
            fallback_ready=groq_ok and ollama_ok,
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
        error_type: str,
        custom_error: Optional[str] = None
    ) -> str:
        """
        Gracefully handles AI provider failures by informing the user
        and providing a structured, grounded synthesis from repository telemetry.
        """
        model_name = self.groq.model if (settings.AI_PROVIDER == "groq") else self.ollama.model
        base_url = self.groq.GROQ_API_BASE if (settings.AI_PROVIDER == "groq") else self.ollama.base_url

        if error_type == "groq_error":
            notice = (
                f"> **Notice:** Groq Cloud LPU is currently unreachable or rate limited ({custom_error or 'Connection issue'}). "
                f"Falling back to grounded telemetry synthesis.\n\n"
            )
        elif error_type == "connection":
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
