"""
Workflow Router — REST API endpoints for workflow management.
All endpoints are scoped to the authenticated client (hardcoded for now).
"""
import json
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.db.session import get_db, get_redis
from app.config import settings
from app.models.workflow import WorkflowCategory, WorkflowStatus
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowSummary, PaginatedWorkflows,
    WorkflowDocumentCreate, WorkflowDocumentUpdate, WorkflowDocumentResponse,
    WorkflowQuestionCreate, WorkflowQuestionUpdate, WorkflowQuestionResponse,
    SessionCreate, SessionResponse,
    CriteriaParseRequest, CriteriaParseResponse,
    DocumentTypeCatalogResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])
log = structlog.get_logger()


# ─── Dependency: get current client_id (hardcoded for now, auth later) ───────

def get_client_id() -> str:
    return settings.DEFAULT_CLIENT_ID


# ─── Workflow CRUD ────────────────────────────────────────────────────────────

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Create a new workflow with documents and questions."""
    service = WorkflowService(db)
    try:
        return await service.create_workflow(client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=PaginatedWorkflows)
async def list_workflows(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: WorkflowCategory | None = Query(None, description="Filter by category"),
    status: WorkflowStatus | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name or description"),
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """List all workflows for the current client with pagination and filtering."""
    service = WorkflowService(db)
    return await service.get_workflows(
        client_id=client_id,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        search=search,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Get a workflow by ID with full details."""
    service = WorkflowService(db)
    try:
        return await service.get_workflow(workflow_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Update workflow metadata (name, description, settings)."""
    service = WorkflowService(db)
    try:
        return await service.update_workflow(workflow_id, client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Delete a workflow and all associated documents/questions."""
    service = WorkflowService(db)
    try:
        await service.delete_workflow(workflow_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workflow_id}/activate", response_model=WorkflowResponse)
async def activate_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Activate a workflow to allow session creation."""
    service = WorkflowService(db)
    try:
        return await service.activate_workflow(workflow_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/duplicate", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Duplicate an existing workflow."""
    service = WorkflowService(db)
    try:
        return await service.duplicate_workflow(workflow_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Documents ────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/documents", response_model=WorkflowDocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_document(
    workflow_id: uuid.UUID,
    data: WorkflowDocumentCreate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Add a document requirement to a workflow."""
    service = WorkflowService(db)
    try:
        return await service.add_document(workflow_id, client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{workflow_id}/documents/{document_id}", response_model=WorkflowDocumentResponse)
async def update_document(
    workflow_id: uuid.UUID,
    document_id: uuid.UUID,
    data: WorkflowDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Update a document requirement in a workflow."""
    service = WorkflowService(db)
    try:
        return await service.update_document(workflow_id, document_id, client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{workflow_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    workflow_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Remove a document requirement from a workflow."""
    service = WorkflowService(db)
    try:
        await service.remove_document(workflow_id, document_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Questions ────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/questions", response_model=WorkflowQuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    workflow_id: uuid.UUID,
    data: WorkflowQuestionCreate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Add a question to a workflow."""
    service = WorkflowService(db)
    try:
        return await service.add_question(workflow_id, client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{workflow_id}/questions/{question_id}", response_model=WorkflowQuestionResponse)
async def update_question(
    workflow_id: uuid.UUID,
    question_id: uuid.UUID,
    data: WorkflowQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Update a question in a workflow."""
    service = WorkflowService(db)
    try:
        return await service.update_question(workflow_id, question_id, client_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{workflow_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_question(
    workflow_id: uuid.UUID,
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Remove a question from a workflow."""
    service = WorkflowService(db)
    try:
        await service.remove_question(workflow_id, question_id, client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Sessions ─────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    workflow_id: uuid.UUID,
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    client_id: str = Depends(get_client_id),
):
    """
    Initiate a new session for a customer on this workflow.
    After persisting the session, publishes a `session.created` event to the
    Redis queue so the Agent Service can pick it up and place the outbound call.
    """
    service = WorkflowService(db)
    try:
        session = await service.create_session(workflow_id, client_id, data)

        # Publish event to agent service queue (LPUSH — agent uses BLPOP)
        event = {
            "session_id":           str(session.id),
            "workflow_id":          str(session.workflow_id),
            "client_id":            session.client_id,
            "customer_phone":       session.customer_phone,
            "customer_name":        session.customer_name,
            "customer_email":       session.customer_email,
            "external_reference_id": session.external_reference_id,
        }
        await redis.lpush(settings.SESSION_CREATED_QUEUE, json.dumps(event))
        log.info(
            "session.created event published",
            session_id=str(session.id),
            queue=settings.SESSION_CREATED_QUEUE,
        )

        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/sessions")
async def list_sessions(
    workflow_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """List all sessions for a workflow."""
    service = WorkflowService(db)
    try:
        return await service.get_sessions(workflow_id, client_id, page, page_size)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Templates ────────────────────────────────────────────────────────────────

@router.get("/templates/list")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """List all available quick-start workflow templates."""
    service = WorkflowService(db)
    return {"templates": await service.get_templates()}


@router.post("/templates/{template_key}/use", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def use_template(
    template_key: str,
    overrides: dict | None = None,
    db: AsyncSession = Depends(get_db),
    client_id: str = Depends(get_client_id),
):
    """Create a new workflow from a quick-start template."""
    service = WorkflowService(db)
    try:
        return await service.create_from_template(client_id, template_key, overrides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Document Catalog ─────────────────────────────────────────────────────────

@router.get("/catalog/documents", response_model=DocumentTypeCatalogResponse)
async def get_document_catalog(
    db: AsyncSession = Depends(get_db),
):
    """Get the full catalog of available document types, grouped by category."""
    service = WorkflowService(db)
    return service.get_document_catalog()


# ─── Criteria Parsing ─────────────────────────────────────────────────────────

@router.post("/criteria/parse", response_model=CriteriaParseResponse)
async def parse_criteria(
    data: CriteriaParseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse natural language criteria text into structured logical conditions."""
    service = WorkflowService(db)
    return service.parse_document_criteria(data)
