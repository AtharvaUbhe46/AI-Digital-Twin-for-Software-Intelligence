import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.project import Project
from app.models.architecture import ArchitectureAnalysis, GraphNode, GraphEdge
from app.models.health import SoftwareHealthSnapshot, HealthDimensionResult
from app.models.risk import SoftwareRisk
from app.models.evolution import DependencyManifest, DependencyItem, ChangeHotspot, TechnicalDebtIndicator
from app.services.assistant.ollama_service import (
    OllamaService,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaServiceError,
)
from app.services.assistant.context_engine import ProjectContextEngine
from app.services.assistant.conversation_manager import ConversationManager
from app.services.assistant.prompt_builder import PromptBuilder, SYSTEM_PROMPT
from app.services.assistant.assistant_service import AIProjectAssistantService

client = TestClient(app)


@pytest.fixture
def sample_project():
    """Seeds a test project with health snapshot, risks, and architecture nodes."""
    db = SessionLocal()
    try:
        project = Project(
            github_owner="test-owner",
            github_repo="test-repo",
            name="test-repo",
            full_name="test-owner/test-repo",
            html_url="https://github.com/test-owner/test-repo",
            is_active=True,
            health_score=82.5,
            open_issues_count=4,
            open_prs_count=2,
            default_branch="main"
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Health Snapshot
        health_snap = SoftwareHealthSnapshot(
            project_id=project.id,
            overall_score=82.5,
            overall_status="HEALTHY",
            explanations=["Activity velocity is consistent with active development."]
        )
        db.add(health_snap)
        db.commit()
        db.refresh(health_snap)

        dim = HealthDimensionResult(
            snapshot_id=health_snap.id,
            dimension="activity",
            name="Activity Velocity",
            score=88.0,
            weight=0.2,
            status="HEALTHY",
            metrics={},
            explanation=["Healthy commit activity."]
        )
        db.add(dim)

        # Risk
        risk = SoftwareRisk(
            project_id=project.id,
            risk_type="STALE_ISSUES",
            title="Stale Issue Backlog",
            description="3 issues have been open for over 60 days.",
            severity="MEDIUM",
            status="OPEN",
            fingerprint="test-fp-1",
            detection_rule="RULE_STALE_ISSUES"
        )
        db.add(risk)

        # Architecture Analysis & Nodes
        arch = ArchitectureAnalysis(
            project_id=project.id,
            status="COMPLETED",
            metrics={
                "total_files": 12,
                "total_modules": 3,
                "total_classes": 8,
                "total_functions": 24,
                "internal_dependencies": 15,
                "modules": [{"name": "app.services", "internal_components": 4, "fan_in": 2, "fan_out": 3}]
            },
            cycles=[]
        )
        db.add(arch)
        db.commit()
        db.refresh(arch)

        node_payment = GraphNode(
            id="class:PaymentService",
            analysis_id=arch.id,
            project_id=project.id,
            node_type="class",
            name="PaymentService",
            file_path="app/services/payment.py",
            module="app.services"
        )
        node_order = GraphNode(
            id="class:OrderController",
            analysis_id=arch.id,
            project_id=project.id,
            node_type="class",
            name="OrderController",
            file_path="app/controllers/order.py",
            module="app.controllers"
        )
        db.add_all([node_payment, node_order])
        db.commit()

        edge = GraphEdge(
            analysis_id=arch.id,
            project_id=project.id,
            source_id="class:OrderController",
            target_id="class:PaymentService",
            relationship_type="DEPENDS_ON",
            confidence=1.0
        )
        db.add(edge)
        db.commit()

        yield project.id
    finally:
        db.close()


# ─── 1. OllamaService Tests ──────────────────────────────────────────────────

def test_ollama_service_check_health_connected():
    service = OllamaService(base_url="http://localhost:11434", model="qwen2.5:7b")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "qwen2.5:7b"}, {"name": "llama3:8b"}]
    }

    with patch("httpx.Client.get", return_value=mock_response):
        status = service.check_health()
        assert status["connected"] is True
        assert status["model_available"] is True
        assert "qwen2.5:7b" in status["available_models"]
        assert status["error"] is None


def test_ollama_service_check_health_model_missing():
    service = OllamaService(base_url="http://localhost:11434", model="qwen3:8b")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "llama3:8b"}]
    }

    with patch("httpx.Client.get", return_value=mock_response):
        status = service.check_health()
        assert status["connected"] is True
        assert status["model_available"] is False
        assert "ollama pull qwen3:8b" in status["error"]


def test_ollama_service_check_health_unreachable():
    import httpx
    service = OllamaService(base_url="http://localhost:11434", model="qwen2.5:7b")

    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        status = service.check_health()
        assert status["connected"] is False
        assert status["model_available"] is False
        assert "Cannot connect to Ollama" in status["error"]


def test_ollama_service_chat_completion_success():
    service = OllamaService(base_url="http://localhost:11434", model="qwen2.5:7b")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "PaymentService is used by 5 components."}
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = service.chat_completion([{"role": "user", "content": "What is PaymentService?"}])
        assert result == "PaymentService is used by 5 components."


def test_ollama_service_chat_completion_errors():
    import httpx
    service = OllamaService(base_url="http://localhost:11434", model="qwen2.5:7b")

    # Connection error
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(OllamaConnectionError) as exc_info:
            service.chat_completion([{"role": "user", "content": "hello"}])
        assert "couldn't connect to the local Qwen model" in str(exc_info.value)

    # 404 model not found
    mock_404 = MagicMock()
    mock_404.status_code = 404
    with patch("httpx.Client.post", return_value=mock_404):
        with pytest.raises(OllamaModelNotFoundError) as exc_info:
            service.chat_completion([{"role": "user", "content": "hello"}])
        assert "ollama pull" in str(exc_info.value)


# ─── 2. Context Engine Tests ─────────────────────────────────────────────────

def test_context_engine_intent_analysis():
    engine = ProjectContextEngine()

    assert engine.analyze_intent("Explain the project architecture")["primary"] == "architecture"
    assert engine.analyze_intent("What depends on PaymentService?")["primary"] == "dependencies"
    assert engine.analyze_intent("Why is this component risky?")["primary"] == "risks"
    assert engine.analyze_intent("How healthy is the codebase?")["primary"] == "health"
    assert engine.analyze_intent("What technical debt should I fix first?")["primary"] == "debt_hotspots"
    assert engine.analyze_intent("Which file implements authentication?")["primary"] == "files"


def test_context_engine_entity_extraction_and_pronouns():
    engine = ProjectContextEngine()

    # CamelCase component name
    assert engine.extract_entity_candidate("What does PaymentService do?") == "PaymentService"

    # Quoted entity
    assert engine.extract_entity_candidate("What happens if I remove '@babel/core'?") == "@babel/core"

    # Package name with scope
    assert engine.extract_entity_candidate("What happens if I remove @babel/core?") == "@babel/core"

    # Referential pronoun resolution
    assert engine.extract_entity_candidate("What depends on it?", previous_entity="PaymentService") == "PaymentService"
    assert engine.extract_entity_candidate("Is this component risky?", previous_entity="OrderController") == "OrderController"


def test_context_engine_build_context(sample_project):
    db = SessionLocal()
    try:
        engine = ProjectContextEngine()
        res = engine.build_project_context(
            project_id=sample_project,
            question="What is PaymentService and what depends on it?",
            db=db
        )

        assert "PROJECT METADATA:" in res["context_text"]
        assert "COMPONENT INTELLIGENCE FOR 'PaymentService':" in res["context_text"]
        assert len(res["sources"]) > 0
        assert "PaymentService" in res["related_components"]
    finally:
        db.close()


# ─── 3. Prompt Builder Tests ─────────────────────────────────────────────────

def test_prompt_builder_structure():
    builder = PromptBuilder()
    question = "What depends on PaymentService?"
    context = "COMPONENT INTELLIGENCE FOR PaymentService: Direct Dependents Count: 3"
    history = [
        {"role": "user", "content": "What is PaymentService?"},
        {"role": "assistant", "content": "PaymentService processes credit card payments."}
    ]

    messages = builder.build_messages(question, context, history)

    # 1 system message, 2 history messages, 1 user message with evidence
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert "GROUNDED IN REALITY" in messages[0]["content"]
    assert "DO NOT DUMP RAW INTERNAL METADATA" in messages[0]["content"]

    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"

    current_turn = messages[3]
    assert current_turn["role"] == "user"
    assert question in current_turn["content"]
    assert context in current_turn["content"]


# ─── 4. Conversation Manager Tests ───────────────────────────────────────────

def test_conversation_manager_multiturn():
    mgr = ConversationManager()
    session = mgr.get_or_create_session(conversation_id=None, project_id=1)
    cid = session.conversation_id

    # Turn 1
    session.add_user_message("What is PaymentService?")
    session.add_assistant_message("PaymentService handles billing.", referenced_entity="PaymentService")

    assert session.last_entity == "PaymentService"
    assert len(session.messages) == 2

    # Turn 2 (referential pronoun)
    session.add_user_message("What depends on it?")
    assert len(session.messages) == 3

    llm_msgs = session.get_messages_for_llm(limit=6)
    assert len(llm_msgs) == 3
    assert llm_msgs[0]["content"] == "What is PaymentService?"

    # Retrieval via manager
    fetched = mgr.get_session(cid)
    assert fetched is session

    # Clear session
    assert mgr.clear_session(cid) is True
    assert mgr.get_session(cid) is None


# ─── 5. Assistant Service & API Endpoints ─────────────────────────────────────

def test_assistant_service_chat_with_mock_ollama(sample_project):
    db = SessionLocal()
    try:
        mock_ollama = MagicMock()
        mock_ollama.chat_completion.return_value = (
            "PaymentService is directly used by OrderController in the architecture.\n\n"
            "Changes to PaymentService should be reviewed carefully."
        )
        mock_ollama.model = "qwen2.5:7b"
        mock_ollama.base_url = "http://localhost:11434"

        service = AIProjectAssistantService(ollama=mock_ollama)
        response = service.chat(
            project_id=sample_project,
            message="Which components depend on PaymentService?",
            db=db
        )

        assert "PaymentService is directly used by" in response.answer
        assert len(response.conversation_id) > 0
        assert len(response.suggested_questions) > 0
        assert mock_ollama.chat_completion.called
    finally:
        db.close()


def test_assistant_service_offline_fallback(sample_project):
    db = SessionLocal()
    try:
        mock_ollama = MagicMock()
        mock_ollama.chat_completion.side_effect = OllamaConnectionError("Cannot connect")
        mock_ollama.model = "qwen2.5:7b"
        mock_ollama.base_url = "http://localhost:11434"

        service = AIProjectAssistantService(ollama=mock_ollama)
        response = service.chat(
            project_id=sample_project,
            message="What is the health of this project?",
            db=db
        )

        assert "couldn't connect to the local Qwen model" in response.answer
        assert "Overall Health Score:" in response.answer
    finally:
        db.close()


def test_api_assistant_chat_endpoint(sample_project):
    with patch("app.services.assistant.assistant_service.ollama_service.chat_completion") as mock_chat:
        mock_chat.return_value = (
            "The repository software health score is currently evaluated at 82.5 out of 100."
        )

        res = client.post(
            f"/api/v1/projects/{sample_project}/assistant/chat",
            json={"message": "What is the health score of this project?"}
        )

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "82.5" in data["answer"]
        assert "conversation_id" in data
        assert isinstance(data["sources"], list)
        assert isinstance(data["suggested_questions"], list)

        # Test conversation history retrieval
        cid = data["conversation_id"]
        res_history = client.get(f"/api/v1/projects/{sample_project}/assistant/conversations/{cid}")
        assert res_history.status_code == 200
        history_data = res_history.json()
        assert len(history_data["messages"]) == 2

        # Test clear conversation
        res_del = client.delete(f"/api/v1/projects/{sample_project}/assistant/conversations/{cid}")
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True


def test_api_assistant_suggested_questions(sample_project):
    res = client.get(f"/api/v1/projects/{sample_project}/assistant/suggested-questions")
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == sample_project
    assert len(data["questions"]) >= 3


def test_api_assistant_status():
    with patch("app.services.assistant.assistant_service.ollama_service.check_health") as mock_health:
        mock_health.return_value = {
            "connected": True,
            "base_url": "http://localhost:11434",
            "model": "qwen2.5:7b",
            "model_available": True,
            "available_models": ["qwen2.5:7b"],
            "error": None
        }

        res = client.get("/api/v1/assistant/status")
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["model"] == "qwen2.5:7b"


def test_context_engine_general_programming_classifier():
    engine = ProjectContextEngine()

    # General programming questions
    assert engine.is_general_programming_question("How do I reverse a string in Python?") is True
    assert engine.is_general_programming_question("What is an event loop in JavaScript?") is True
    assert engine.is_general_programming_question("Explain polymorphism in Java") is True
    assert engine.is_general_programming_question("What is a Promise in JS?") is True

    # Project-specific questions
    assert engine.is_general_programming_question("What is the architecture of this project?") is False
    assert engine.is_general_programming_question("What are the API endpoints in this app?") is False
    assert engine.is_general_programming_question("What is the health score of the repository?") is False
    assert engine.is_general_programming_question("Are there circular dependencies?") is False
    assert engine.is_general_programming_question("What packages or dependencies are tracked?") is False


def test_api_assistant_stream_endpoint(sample_project):
    async def mock_async_stream(*args, **kwargs):
        yield "PaymentService "
        yield "is a core "
        yield "component."

    with patch("app.services.assistant.assistant_service.ollama_service.chat_stream", side_effect=mock_async_stream):
        res = client.post(
            f"/api/v1/projects/{sample_project}/assistant/stream",
            json={"message": "What is PaymentService?"}
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert "data: " in body
        assert '"event": "start"' in body
        assert '"event": "sources"' in body
        assert '"event": "token"' in body
        assert '"event": "done"' in body
