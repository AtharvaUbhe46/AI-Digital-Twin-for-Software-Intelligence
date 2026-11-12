import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    OllamaStatusResponse,
    ConversationHistoryResponse,
    SuggestedQuestionsResponse,
)
from app.services.assistant.assistant_service import assistant_service

logger = logging.getLogger("digital_twin.api.assistant")
router = APIRouter()


@router.post(
    "/projects/{project_id}/assistant/chat",
    response_model=AssistantChatResponse,
    summary="Ask Question to AI Project Assistant",
    description="Asks a natural-language question about the project's architecture, dependencies, health, risks, and code.",
)
async def chat_with_project_assistant(
    project_id: int,
    payload: AssistantChatRequest,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        response = assistant_service.chat(
            project_id=project_id,
            message=payload.message,
            db=db,
            conversation_id=payload.conversation_id,
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error handling assistant chat for project {project_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant service error")


@router.post(
    "/assistant/chat",
    response_model=AssistantChatResponse,
    summary="Ask Question (Active Project Fallback)",
    description="Conversational endpoint that automatically targets the currently active project or project_id in payload.",
)
async def chat_with_assistant_active(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    target_id = payload.project_id
    if not target_id:
        active = db.query(Project).filter(Project.is_active == True).first()
        if not active:
            active = db.query(Project).first()
        if not active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active project found in system")
        target_id = active.id

    return await chat_with_project_assistant(project_id=target_id, payload=payload, db=db)


@router.post(
    "/projects/{project_id}/assistant/stream",
    summary="Stream Question to AI Project Assistant",
    description="Streams real-time SSE tokens for a natural-language question about the project.",
)
async def stream_project_assistant(
    project_id: int,
    payload: AssistantChatRequest,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    async def event_generator():
        try:
            async for event_dict in assistant_service.chat_stream(
                project_id=project_id,
                message=payload.message,
                db=db,
                conversation_id=payload.conversation_id,
            ):
                yield f"data: {json.dumps(event_dict)}\n\n"
        except Exception as exc:
            logger.error(f"Error during assistant event stream for project {project_id}: {exc}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post(
    "/assistant/stream",
    summary="Stream Question (Active Project Fallback)",
    description="Streaming SSE endpoint that automatically targets the active project or project_id in payload.",
)
async def stream_assistant_active(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    target_id = payload.project_id
    if not target_id:
        active = db.query(Project).filter(Project.is_active == True).first()
        if not active:
            active = db.query(Project).first()
        if not active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active project found in system")
        target_id = active.id

    return await stream_project_assistant(project_id=target_id, payload=payload, db=db)


@router.get(
    "/projects/{project_id}/assistant/suggested-questions",
    response_model=SuggestedQuestionsResponse,
    summary="Get Contextual Suggested Questions",
    description="Returns intelligent suggested questions derived from actual project architecture and health telemetry.",
)
async def get_suggested_questions(
    project_id: int,
    db: Session = Depends(get_db)
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    return assistant_service.get_suggested_questions(project_id=project_id, db=db)


@router.get(
    "/projects/{project_id}/assistant/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    summary="Get Conversation History",
    description="Retrieves the chronological message turns for a conversation session.",
)
async def get_conversation_history(
    project_id: int,
    conversation_id: str,
):
    return assistant_service.get_conversation_history(conversation_id=conversation_id, project_id=project_id)


@router.delete(
    "/projects/{project_id}/assistant/conversations/{conversation_id}",
    summary="Clear Conversation Session",
    description="Clears an active conversation session history.",
)
async def clear_conversation(
    project_id: int,
    conversation_id: str,
):
    success = assistant_service.clear_conversation(conversation_id=conversation_id)
    return {"success": success, "conversation_id": conversation_id}


@router.get(
    "/assistant/status",
    response_model=OllamaStatusResponse,
    summary="Get Ollama & Qwen Status",
    description="Returns connectivity status of the local Ollama daemon and whether the configured Qwen model is available.",
)
async def get_assistant_status():
    return assistant_service.get_status()
