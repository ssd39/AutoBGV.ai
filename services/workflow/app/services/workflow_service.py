"""
Workflow Service — Business logic layer for workflow CRUD,
criteria parsing, template management, and session initiation.
"""
import math
import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
import redis.asyncio as aioredis

from app.models.workflow import (
    Workflow, WorkflowDocument, WorkflowQuestion, WorkflowSession,
    WorkflowStatus, WorkflowCategory, DocumentCategory, QuestionType, SessionStatus,
)
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate,
    WorkflowDocumentCreate, WorkflowDocumentUpdate,
    WorkflowQuestionCreate, WorkflowQuestionUpdate,
    WorkflowResponse, WorkflowSummary, PaginatedWorkflows,
    SessionCreate, SessionResponse,
    CriteriaParseRequest, CriteriaParseResponse,
    LogicalCriteria, CriteriaCondition,
    WorkflowDocumentResponse, WorkflowQuestionResponse,
    DocumentTypeInfo, DocumentTypeCatalogResponse,
)
from app.constants.documents import DOCUMENT_TYPES, DOCUMENTS_BY_CATEGORY
from app.constants.templates import WORKFLOW_TEMPLATES, get_template


# ─── Criteria Parser (Rule-based; LLM to be integrated later) ────────────────

CRITERIA_KEYWORDS: dict[str, dict[str, Any]] = {
    # Expiry / validity
    r"not expired|must not be expired|should not be expired|valid": {
        "field": "expiry_date",
        "operator": "gt",
        "value": "today",
        "description": "Document must not be expired",
    },
    r"not older than (\d+) months?": {
        "field": "issue_date",
        "operator": "gte",
        "value": "today - {1} months",
        "description": "Document issue date within last {1} months",
        "dynamic": True,
    },
    r"not older than (\d+) years?": {
        "field": "issue_date",
        "operator": "gte",
        "value": "today - {1} years",
        "description": "Document issue date within last {1} years",
        "dynamic": True,
    },
    # Name matching
    r"name must match|name should match|name matches?": {
        "field": "name_match",
        "operator": "eq",
        "value": "applicant_name",
        "description": "Name on document must match applicant name",
    },
    # Photo
    r"photo (must|should) be (clearly )?visible|photo visible|clear photo": {
        "field": "photo_present",
        "operator": "eq",
        "value": True,
        "description": "Photo must be clearly visible",
    },
    # Original / copy
    r"original (document|copy)|not a photocopy|no photocopy": {
        "field": "document_type",
        "operator": "eq",
        "value": "original",
        "description": "Must be original document, not a photocopy",
    },
    r"certified copy|self.?attested": {
        "field": "document_type",
        "operator": "in",
        "value": ["original", "certified_copy", "self_attested"],
        "description": "Original or certified copy accepted",
    },
    # Address
    r"address must match|address should match|same address": {
        "field": "address_match",
        "operator": "eq",
        "value": "application_address",
        "description": "Address on document must match application",
    },
    # Signature / stamp
    r"(signed|signature) by (employer|doctor|bank|authority)": {
        "field": "signature_present",
        "operator": "eq",
        "value": True,
        "description": "Must be signed by authorized authority",
    },
    r"(stamped|stamp) by (employer|hospital|bank)": {
        "field": "stamp_present",
        "operator": "eq",
        "value": True,
        "description": "Must be stamped by issuing authority",
    },
    # Both sides
    r"both sides|front and back": {
        "field": "both_sides_provided",
        "operator": "eq",
        "value": True,
        "description": "Both front and back of the document required",
    },
    # PAN specific
    r"pan (must be |should be )?valid|active pan": {
        "field": "pan_status",
        "operator": "eq",
        "value": "active",
        "description": "PAN must be valid and active",
    },
    # GST specific
    r"gst (must be |should be )?active|active gst": {
        "field": "gst_status",
        "operator": "eq",
        "value": "active",
        "description": "GST registration must be active",
    },
    # Bank specific
    r"ifsc (code|number)": {
        "field": "ifsc_present",
        "operator": "eq",
        "value": True,
        "description": "IFSC code must be visible",
    },
    # Legibility
    r"clearly (readable|legible|visible)|all details (must be |should be )?readable": {
        "field": "legibility",
        "operator": "eq",
        "value": "clear",
        "description": "All text must be clearly readable",
    },
}


def parse_criteria(criteria_text: str, document_type_key: str) -> LogicalCriteria:
    """
    Parse natural language criteria text into structured logical conditions.
    Uses rule-based pattern matching.
    TODO: Replace/augment with LLM-based parsing for higher accuracy.
    """
    conditions: list[CriteriaCondition] = []
    text_lower = criteria_text.lower().strip()

    for pattern, condition_template in CRITERIA_KEYWORDS.items():
        match = re.search(pattern, text_lower)
        if match:
            if condition_template.get("dynamic") and match.groups():
                # Handle dynamic values like "today - 3 months"
                group_val = match.group(1)
                description = condition_template["description"].replace("{1}", group_val)
                value = condition_template["value"].replace("{1}", group_val)
                conditions.append(CriteriaCondition(
                    field=condition_template["field"],
                    operator=condition_template["operator"],
                    value=value,
                    description=description,
                ))
            else:
                conditions.append(CriteriaCondition(
                    field=condition_template["field"],
                    operator=condition_template["operator"],
                    value=condition_template["value"],
                    description=condition_template["description"],
                ))

    return LogicalCriteria(
        raw_text=criteria_text,
        conditions=conditions,
        logic="AND",
    )


# ─── Workflow Service ─────────────────────────────────────────────────────────

class WorkflowService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None):
        self.db = db
        self.redis = redis

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _get_workflow_or_404(self, workflow_id: uuid.UUID, client_id: str) -> Workflow:
        stmt = (
            select(Workflow)
            .options(
                selectinload(Workflow.documents),
                selectinload(Workflow.questions),
            )
            .where(Workflow.id == workflow_id, Workflow.client_id == client_id)
        )
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow

    def _workflow_to_response(self, workflow: Workflow) -> WorkflowResponse:
        return WorkflowResponse(
            id=workflow.id,
            client_id=workflow.client_id,
            name=workflow.name,
            description=workflow.description,
            category=workflow.category,
            status=workflow.status,
            is_template=workflow.is_template,
            template_key=workflow.template_key,
            welcome_message=workflow.welcome_message,
            completion_message=workflow.completion_message,
            max_retry_attempts=workflow.max_retry_attempts,
            session_timeout_minutes=workflow.session_timeout_minutes,
            documents=[WorkflowDocumentResponse.model_validate(d) for d in workflow.documents],
            questions=[WorkflowQuestionResponse.model_validate(q) for q in workflow.questions],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _workflow_to_summary(self, workflow: Workflow, doc_count: int = 0, q_count: int = 0, s_count: int = 0) -> WorkflowSummary:
        return WorkflowSummary(
            id=workflow.id,
            client_id=workflow.client_id,
            name=workflow.name,
            description=workflow.description,
            category=workflow.category,
            status=workflow.status,
            is_template=workflow.is_template,
            template_key=workflow.template_key,
            document_count=doc_count,
            question_count=q_count,
            session_count=s_count,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def create_workflow(self, client_id: str, data: WorkflowCreate) -> WorkflowResponse:
        workflow = Workflow(
            client_id=client_id,
            name=data.name,
            description=data.description,
            category=data.category,
            status=data.status,
            welcome_message=data.welcome_message,
            completion_message=data.completion_message,
            max_retry_attempts=data.max_retry_attempts,
            session_timeout_minutes=data.session_timeout_minutes,
        )
        self.db.add(workflow)
        await self.db.flush()  # get the workflow ID

        # Add documents
        for i, doc_data in enumerate(data.documents):
            logical = None
            if doc_data.criteria_text:
                parsed = parse_criteria(doc_data.criteria_text, doc_data.document_type_key)
                logical = parsed.model_dump()

            doc = WorkflowDocument(
                workflow_id=workflow.id,
                document_type_key=doc_data.document_type_key,
                display_name=doc_data.display_name,
                document_category=doc_data.document_category,
                description=doc_data.description,
                is_required=doc_data.is_required,
                order_index=doc_data.order_index if doc_data.order_index != 0 else i,
                criteria_text=doc_data.criteria_text,
                logical_criteria=logical,
                allowed_formats=doc_data.allowed_formats,
                max_file_size_mb=doc_data.max_file_size_mb,
                instructions=doc_data.instructions,
            )
            self.db.add(doc)

        # Add questions
        for i, q_data in enumerate(data.questions):
            q = WorkflowQuestion(
                workflow_id=workflow.id,
                question_text=q_data.question_text,
                question_type=q_data.question_type,
                options=q_data.options,
                is_required=q_data.is_required,
                order_index=q_data.order_index if q_data.order_index != 0 else i,
                helper_text=q_data.helper_text,
                validation_rules=q_data.validation_rules,
            )
            self.db.add(q)

        await self.db.commit()
        # Re-fetch so all columns (created_at, updated_at, etc.) are fresh without triggering lazy loads
        workflow = await self._get_workflow_or_404(workflow.id, client_id)
        return self._workflow_to_response(workflow)

    async def get_workflows(
        self,
        client_id: str,
        page: int = 1,
        page_size: int = 20,
        category: WorkflowCategory | None = None,
        status: WorkflowStatus | None = None,
        search: str | None = None,
    ) -> PaginatedWorkflows:
        # Count subquery for docs, questions, sessions
        doc_count_sq = (
            select(WorkflowDocument.workflow_id, func.count().label("doc_count"))
            .group_by(WorkflowDocument.workflow_id)
            .subquery()
        )
        q_count_sq = (
            select(WorkflowQuestion.workflow_id, func.count().label("q_count"))
            .group_by(WorkflowQuestion.workflow_id)
            .subquery()
        )
        s_count_sq = (
            select(WorkflowSession.workflow_id, func.count().label("s_count"))
            .group_by(WorkflowSession.workflow_id)
            .subquery()
        )

        base_stmt = (
            select(
                Workflow,
                func.coalesce(doc_count_sq.c.doc_count, 0).label("doc_count"),
                func.coalesce(q_count_sq.c.q_count, 0).label("q_count"),
                func.coalesce(s_count_sq.c.s_count, 0).label("s_count"),
            )
            .outerjoin(doc_count_sq, Workflow.id == doc_count_sq.c.workflow_id)
            .outerjoin(q_count_sq, Workflow.id == q_count_sq.c.workflow_id)
            .outerjoin(s_count_sq, Workflow.id == s_count_sq.c.workflow_id)
            .where(Workflow.client_id == client_id, Workflow.is_template == False)
        )

        if category:
            base_stmt = base_stmt.where(Workflow.category == category)
        if status:
            base_stmt = base_stmt.where(Workflow.status == status)
        if search:
            base_stmt = base_stmt.where(
                Workflow.name.ilike(f"%{search}%") | Workflow.description.ilike(f"%{search}%")
            )

        # Total count
        count_stmt = select(func.count()).select_from(
            base_stmt.subquery()
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        paginated_stmt = (
            base_stmt
            .order_by(Workflow.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.db.execute(paginated_stmt)).all()

        items = [
            self._workflow_to_summary(row.Workflow, row.doc_count, row.q_count, row.s_count)
            for row in rows
        ]

        return PaginatedWorkflows(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total > 0 else 0,
        )

    async def get_workflow(self, workflow_id: uuid.UUID, client_id: str) -> WorkflowResponse:
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        return self._workflow_to_response(workflow)

    async def update_workflow(
        self, workflow_id: uuid.UUID, client_id: str, data: WorkflowUpdate
    ) -> WorkflowResponse:
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(workflow, key, value)
        await self.db.commit()
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        return self._workflow_to_response(workflow)

    async def delete_workflow(self, workflow_id: uuid.UUID, client_id: str) -> None:
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        await self.db.delete(workflow)
        await self.db.commit()

    async def activate_workflow(self, workflow_id: uuid.UUID, client_id: str) -> WorkflowResponse:
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        if not workflow.documents:
            raise ValueError("Cannot activate a workflow with no documents")
        workflow.status = WorkflowStatus.ACTIVE
        await self.db.commit()
        workflow = await self._get_workflow_or_404(workflow_id, client_id)
        return self._workflow_to_response(workflow)

    async def duplicate_workflow(self, workflow_id: uuid.UUID, client_id: str) -> WorkflowResponse:
        """Create a copy of an existing workflow."""
        original = await self._get_workflow_or_404(workflow_id, client_id)
        new_workflow = Workflow(
            client_id=client_id,
            name=f"{original.name} (Copy)",
            description=original.description,
            category=original.category,
            status=WorkflowStatus.DRAFT,
            welcome_message=original.welcome_message,
            completion_message=original.completion_message,
            max_retry_attempts=original.max_retry_attempts,
            session_timeout_minutes=original.session_timeout_minutes,
        )
        self.db.add(new_workflow)
        await self.db.flush()

        for doc in original.documents:
            new_doc = WorkflowDocument(
                workflow_id=new_workflow.id,
                document_type_key=doc.document_type_key,
                display_name=doc.display_name,
                document_category=doc.document_category,
                description=doc.description,
                is_required=doc.is_required,
                order_index=doc.order_index,
                criteria_text=doc.criteria_text,
                logical_criteria=doc.logical_criteria,
                allowed_formats=doc.allowed_formats,
                max_file_size_mb=doc.max_file_size_mb,
                instructions=doc.instructions,
            )
            self.db.add(new_doc)

        for q in original.questions:
            new_q = WorkflowQuestion(
                workflow_id=new_workflow.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                order_index=q.order_index,
                helper_text=q.helper_text,
                validation_rules=q.validation_rules,
            )
            self.db.add(new_q)

        await self.db.commit()
        new_workflow = await self._get_workflow_or_404(new_workflow.id, client_id)
        return self._workflow_to_response(new_workflow)

    # ─── Documents ────────────────────────────────────────────────────────────

    async def add_document(
        self, workflow_id: uuid.UUID, client_id: str, data: WorkflowDocumentCreate
    ) -> WorkflowDocumentResponse:
        # Validate workflow ownership
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.client_id == client_id)
        workflow = (await self.db.execute(stmt)).scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        logical = None
        if data.criteria_text:
            parsed = parse_criteria(data.criteria_text, data.document_type_key)
            logical = parsed.model_dump()

        doc = WorkflowDocument(
            workflow_id=workflow_id,
            document_type_key=data.document_type_key,
            display_name=data.display_name,
            document_category=data.document_category,
            description=data.description,
            is_required=data.is_required,
            order_index=data.order_index,
            criteria_text=data.criteria_text,
            logical_criteria=logical,
            allowed_formats=data.allowed_formats,
            max_file_size_mb=data.max_file_size_mb,
            instructions=data.instructions,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return WorkflowDocumentResponse.model_validate(doc)

    async def update_document(
        self,
        workflow_id: uuid.UUID,
        document_id: uuid.UUID,
        client_id: str,
        data: WorkflowDocumentUpdate,
    ) -> WorkflowDocumentResponse:
        stmt = (
            select(WorkflowDocument)
            .join(Workflow, WorkflowDocument.workflow_id == Workflow.id)
            .where(
                WorkflowDocument.id == document_id,
                WorkflowDocument.workflow_id == workflow_id,
                Workflow.client_id == client_id,
            )
        )
        doc = (await self.db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Re-parse criteria if updated
        if "criteria_text" in update_data and update_data["criteria_text"]:
            parsed = parse_criteria(update_data["criteria_text"], doc.document_type_key)
            update_data["logical_criteria"] = parsed.model_dump()

        for key, value in update_data.items():
            setattr(doc, key, value)

        await self.db.commit()
        await self.db.refresh(doc)
        return WorkflowDocumentResponse.model_validate(doc)

    async def remove_document(
        self, workflow_id: uuid.UUID, document_id: uuid.UUID, client_id: str
    ) -> None:
        stmt = (
            select(WorkflowDocument)
            .join(Workflow, WorkflowDocument.workflow_id == Workflow.id)
            .where(
                WorkflowDocument.id == document_id,
                WorkflowDocument.workflow_id == workflow_id,
                Workflow.client_id == client_id,
            )
        )
        doc = (await self.db.execute(stmt)).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        await self.db.delete(doc)
        await self.db.commit()

    # ─── Questions ────────────────────────────────────────────────────────────

    async def add_question(
        self, workflow_id: uuid.UUID, client_id: str, data: WorkflowQuestionCreate
    ) -> WorkflowQuestionResponse:
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.client_id == client_id)
        workflow = (await self.db.execute(stmt)).scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        q = WorkflowQuestion(
            workflow_id=workflow_id,
            question_text=data.question_text,
            question_type=data.question_type,
            options=data.options,
            is_required=data.is_required,
            order_index=data.order_index,
            helper_text=data.helper_text,
            validation_rules=data.validation_rules,
        )
        self.db.add(q)
        await self.db.commit()
        await self.db.refresh(q)
        return WorkflowQuestionResponse.model_validate(q)

    async def update_question(
        self,
        workflow_id: uuid.UUID,
        question_id: uuid.UUID,
        client_id: str,
        data: WorkflowQuestionUpdate,
    ) -> WorkflowQuestionResponse:
        stmt = (
            select(WorkflowQuestion)
            .join(Workflow, WorkflowQuestion.workflow_id == Workflow.id)
            .where(
                WorkflowQuestion.id == question_id,
                WorkflowQuestion.workflow_id == workflow_id,
                Workflow.client_id == client_id,
            )
        )
        q = (await self.db.execute(stmt)).scalar_one_or_none()
        if not q:
            raise ValueError(f"Question {question_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(q, key, value)

        await self.db.commit()
        await self.db.refresh(q)
        return WorkflowQuestionResponse.model_validate(q)

    async def remove_question(
        self, workflow_id: uuid.UUID, question_id: uuid.UUID, client_id: str
    ) -> None:
        stmt = (
            select(WorkflowQuestion)
            .join(Workflow, WorkflowQuestion.workflow_id == Workflow.id)
            .where(
                WorkflowQuestion.id == question_id,
                WorkflowQuestion.workflow_id == workflow_id,
                Workflow.client_id == client_id,
            )
        )
        q = (await self.db.execute(stmt)).scalar_one_or_none()
        if not q:
            raise ValueError(f"Question {question_id} not found")
        await self.db.delete(q)
        await self.db.commit()

    # ─── Templates ────────────────────────────────────────────────────────────

    async def get_templates(self) -> list[dict]:
        """Return the list of quick-start template metadata."""
        return [
            {
                "template_key": t["template_key"],
                "name": t["name"],
                "description": t["description"],
                "category": t["category"],
                "document_count": len(t.get("documents", [])),
                "question_count": len(t.get("questions", [])),
            }
            for t in WORKFLOW_TEMPLATES
        ]

    async def create_from_template(
        self, client_id: str, template_key: str, overrides: dict | None = None
    ) -> WorkflowResponse:
        """Create a new workflow from a predefined template."""
        template = get_template(template_key)
        if not template:
            raise ValueError(f"Template '{template_key}' not found")

        # Build WorkflowCreate from template data + overrides
        workflow_data = {**template}
        if overrides:
            workflow_data.update(overrides)

        # Convert documents
        docs = [WorkflowDocumentCreate(**doc) for doc in workflow_data.get("documents", [])]
        # Convert questions
        questions = [WorkflowQuestionCreate(**q) for q in workflow_data.get("questions", [])]

        create_data = WorkflowCreate(
            name=workflow_data.get("name", "Untitled Workflow"),
            description=workflow_data.get("description"),
            category=workflow_data.get("category", "custom"),
            status=WorkflowStatus.DRAFT,
            welcome_message=workflow_data.get("welcome_message"),
            completion_message=workflow_data.get("completion_message"),
            max_retry_attempts=workflow_data.get("max_retry_attempts", 3),
            session_timeout_minutes=workflow_data.get("session_timeout_minutes", 60),
            documents=docs,
            questions=questions,
        )
        return await self.create_workflow(client_id, create_data)

    # ─── Sessions ─────────────────────────────────────────────────────────────

    async def create_session(
        self, workflow_id: uuid.UUID, client_id: str, data: SessionCreate
    ) -> SessionResponse:
        # Validate workflow is active
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.client_id == client_id)
        workflow = (await self.db.execute(stmt)).scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        if workflow.status != WorkflowStatus.ACTIVE:
            raise ValueError("Workflow must be active to create a session")

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=workflow.session_timeout_minutes)

        session = WorkflowSession(
            workflow_id=workflow_id,
            client_id=client_id,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            customer_email=data.customer_email,
            external_reference_id=data.external_reference_id,
            status=SessionStatus.PENDING,
            expires_at=expires_at,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return SessionResponse.model_validate(session)

    async def get_sessions(
        self, workflow_id: uuid.UUID, client_id: str, page: int = 1, page_size: int = 20
    ) -> dict:
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.client_id == client_id)
        workflow = (await self.db.execute(stmt)).scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        count_stmt = select(func.count(WorkflowSession.id)).where(
            WorkflowSession.workflow_id == workflow_id
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        sessions_stmt = (
            select(WorkflowSession)
            .where(WorkflowSession.workflow_id == workflow_id)
            .order_by(WorkflowSession.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(sessions_stmt)).scalars().all()
        return {
            "items": [SessionResponse.model_validate(s) for s in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        }

    # ─── Document Catalog ─────────────────────────────────────────────────────

    def get_document_catalog(self) -> DocumentTypeCatalogResponse:
        categories: dict[str, list[DocumentTypeInfo]] = {}
        for category, docs in DOCUMENTS_BY_CATEGORY.items():
            categories[category] = [DocumentTypeInfo(**doc) for doc in docs]
        return DocumentTypeCatalogResponse(
            categories=categories,
            total=sum(len(v) for v in categories.values()),
        )

    # ─── Criteria Parsing ─────────────────────────────────────────────────────

    def parse_document_criteria(self, data: CriteriaParseRequest) -> CriteriaParseResponse:
        logical = parse_criteria(data.criteria_text, data.document_type_key)
        confidence = min(1.0, len(logical.conditions) * 0.25) if logical.conditions else 0.1
        return CriteriaParseResponse(
            criteria_text=data.criteria_text,
            logical_criteria=logical,
            confidence=confidence,
        )
