"""
Pydantic v2 schemas for the Workflow Service.
These define the request/response shapes for the API.
"""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.models.workflow import (
    WorkflowStatus,
    WorkflowCategory,
    DocumentCategory,
    QuestionType,
    SessionStatus,
)


# ─── Logical Criteria ────────────────────────────────────────────────────────

class CriteriaCondition(BaseModel):
    """A single parsed condition from natural language criteria."""
    field: str = Field(..., description="Field being evaluated, e.g. 'expiry_date', 'name_match'")
    operator: str = Field(
        ...,
        description="Comparison operator: gt, lt, eq, neq, gte, lte, contains, exists, not_exists, matches"
    )
    value: Any = Field(None, description="Value to compare against")
    description: str = Field("", description="Human-readable description of this condition")

    model_config = ConfigDict(from_attributes=True)


class LogicalCriteria(BaseModel):
    """Structured logical criteria derived from natural language input."""
    raw_text: str = Field(..., description="Original natural language criteria text")
    conditions: list[CriteriaCondition] = Field(
        default_factory=list,
        description="List of parsed conditions"
    )
    logic: str = Field("AND", description="How conditions combine: AND | OR")

    model_config = ConfigDict(from_attributes=True)


# ─── Document Schemas ─────────────────────────────────────────────────────────

class WorkflowDocumentCreate(BaseModel):
    document_type_key: str = Field(..., min_length=1, max_length=100, description="Key from document type registry")
    display_name: str = Field(..., min_length=1, max_length=200)
    document_category: DocumentCategory
    description: str | None = Field(None, max_length=1000)
    is_required: bool = True
    order_index: int = Field(0, ge=0)
    criteria_text: str | None = Field(
        None,
        description="Natural language criteria, e.g. 'must not be expired, name must match applicant name'"
    )
    logical_criteria: dict[str, Any] | None = None
    allowed_formats: list[str] = Field(default_factory=lambda: ["jpg", "jpeg", "png", "pdf"])
    max_file_size_mb: int = Field(10, ge=1, le=50)
    instructions: str | None = Field(None, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class WorkflowDocumentUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    is_required: bool | None = None
    order_index: int | None = Field(None, ge=0)
    criteria_text: str | None = None
    logical_criteria: dict[str, Any] | None = None
    allowed_formats: list[str] | None = None
    max_file_size_mb: int | None = Field(None, ge=1, le=50)
    instructions: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowDocumentResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    document_type_key: str
    display_name: str
    document_category: DocumentCategory
    description: str | None
    is_required: bool
    order_index: int
    criteria_text: str | None
    logical_criteria: dict[str, Any] | None
    allowed_formats: list[str] | None
    max_file_size_mb: int
    instructions: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Question Schemas ─────────────────────────────────────────────────────────

class WorkflowQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=5, max_length=1000)
    question_type: QuestionType = QuestionType.TEXT
    options: list[str] | None = Field(None, description="Required for multiple_choice type")
    is_required: bool = True
    order_index: int = Field(0, ge=0)
    helper_text: str | None = Field(None, max_length=500)
    validation_rules: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_options_for_multiple_choice(self) -> "WorkflowQuestionCreate":
        if self.question_type == QuestionType.MULTIPLE_CHOICE:
            if not self.options or len(self.options) < 2:
                raise ValueError("Multiple choice questions must have at least 2 options")
        return self

    model_config = ConfigDict(from_attributes=True)


class WorkflowQuestionUpdate(BaseModel):
    question_text: str | None = Field(None, min_length=5, max_length=1000)
    question_type: QuestionType | None = None
    options: list[str] | None = None
    is_required: bool | None = None
    order_index: int | None = Field(None, ge=0)
    helper_text: str | None = None
    validation_rules: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowQuestionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    question_text: str
    question_type: QuestionType
    options: list[str] | None
    is_required: bool
    order_index: int
    helper_text: str | None
    validation_rules: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Workflow Schemas ─────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200, description="Workflow name")
    description: str | None = Field(None, max_length=2000)
    category: WorkflowCategory = WorkflowCategory.CUSTOM
    status: WorkflowStatus = WorkflowStatus.DRAFT
    welcome_message: str | None = Field(None, max_length=1000)
    completion_message: str | None = Field(None, max_length=1000)
    max_retry_attempts: int = Field(3, ge=1, le=10)
    session_timeout_minutes: int = Field(60, ge=5, le=1440)
    documents: list[WorkflowDocumentCreate] = Field(default_factory=list)
    questions: list[WorkflowQuestionCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = None
    category: WorkflowCategory | None = None
    status: WorkflowStatus | None = None
    welcome_message: str | None = None
    completion_message: str | None = None
    max_retry_attempts: int | None = Field(None, ge=1, le=10)
    session_timeout_minutes: int | None = Field(None, ge=5, le=1440)

    model_config = ConfigDict(from_attributes=True)


class WorkflowSummary(BaseModel):
    """Lightweight workflow summary for list views."""
    id: uuid.UUID
    client_id: str
    name: str
    description: str | None
    category: WorkflowCategory
    status: WorkflowStatus
    is_template: bool
    template_key: str | None
    document_count: int = 0
    question_count: int = 0
    session_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowResponse(BaseModel):
    """Full workflow detail with documents and questions."""
    id: uuid.UUID
    client_id: str
    name: str
    description: str | None
    category: WorkflowCategory
    status: WorkflowStatus
    is_template: bool
    template_key: str | None
    welcome_message: str | None
    completion_message: str | None
    max_retry_attempts: int
    session_timeout_minutes: int
    documents: list[WorkflowDocumentResponse] = []
    questions: list[WorkflowQuestionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Session Schemas ──────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    customer_name: str | None = Field(None, max_length=200)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_email: str | None = Field(None, max_length=200)
    external_reference_id: str | None = Field(None, max_length=200)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace("+", "").replace("-", "").replace(" ", "")
        if not cleaned.isdigit():
            raise ValueError("Phone number must contain only digits")
        return v

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    client_id: str
    customer_name: str | None
    customer_phone: str
    customer_email: str | None
    external_reference_id: str | None
    status: SessionStatus
    question_answers: dict[str, Any] | None
    documents_status: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Document Type Catalog Schemas ───────────────────────────────────────────

class DocumentTypeInfo(BaseModel):
    """Schema for document type catalog entry returned by the API."""
    key: str
    name: str
    category: str
    description: str
    issuing_authority: str
    is_ovi: bool
    is_opa: bool
    common_fields: list[str]

    model_config = ConfigDict(from_attributes=True)


class DocumentTypeCatalogResponse(BaseModel):
    """Grouped catalog of all available document types."""
    categories: dict[str, list[DocumentTypeInfo]]
    total: int

    model_config = ConfigDict(from_attributes=True)


# ─── Template Schemas ─────────────────────────────────────────────────────────

class WorkflowTemplateCreate(WorkflowCreate):
    """Schema for creating from a template — extends WorkflowCreate with template info."""
    template_key: str = Field(..., description="Template identifier to clone from")
    is_template: bool = False  # the clone is not a template


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedWorkflows(BaseModel):
    items: list[WorkflowSummary]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# ─── Criteria Parse Request ───────────────────────────────────────────────────

class CriteriaParseRequest(BaseModel):
    criteria_text: str = Field(
        ..., min_length=5,
        description="Natural language criteria to be parsed into logical conditions"
    )
    document_type_key: str = Field(
        ..., description="The document type this criteria applies to"
    )


class CriteriaParseResponse(BaseModel):
    criteria_text: str
    logical_criteria: LogicalCriteria
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score of the parse")
