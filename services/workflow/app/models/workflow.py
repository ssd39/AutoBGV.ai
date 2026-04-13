import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey,
    Integer, Enum as SAEnum, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class WorkflowCategory(str, enum.Enum):
    KYC = "kyc"
    LOAN = "loan"
    INSURANCE = "insurance"
    BACKGROUND_CHECK = "background_check"
    PROPERTY = "property"
    BUSINESS = "business"
    CUSTOM = "custom"


class DocumentCategory(str, enum.Enum):
    IDENTITY = "identity"
    ADDRESS = "address"
    INCOME = "income"
    BUSINESS = "business"
    PROPERTY = "property"
    VEHICLE = "vehicle"
    MEDICAL = "medical"
    AGRICULTURE = "agriculture"
    OTHER = "other"


class QuestionType(str, enum.Enum):
    TEXT = "text"
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"
    DATE = "date"


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ─── Models ───────────────────────────────────────────────────────────────────

class Workflow(Base):
    """
    A Workflow defines the set of documents and questions required
    for a specific verification process (e.g., loan KYC, insurance claim).
    """
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[WorkflowCategory] = mapped_column(
        SAEnum(WorkflowCategory), nullable=False, default=WorkflowCategory.CUSTOM
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT
    )
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_key: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "loan_kyc"
    # Quick settings
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_retry_attempts: Mapped[int] = mapped_column(Integer, default=3)
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=60)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    documents: Mapped[list["WorkflowDocument"]] = relationship(
        "WorkflowDocument", back_populates="workflow",
        cascade="all, delete-orphan", order_by="WorkflowDocument.order_index"
    )
    questions: Mapped[list["WorkflowQuestion"]] = relationship(
        "WorkflowQuestion", back_populates="workflow",
        cascade="all, delete-orphan", order_by="WorkflowQuestion.order_index"
    )
    sessions: Mapped[list["WorkflowSession"]] = relationship(
        "WorkflowSession", back_populates="workflow"
    )

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} name={self.name} status={self.status}>"


class WorkflowDocument(Base):
    """
    A document requirement within a workflow.
    Stores both the natural language criteria and the parsed logical criteria.
    """
    __tablename__ = "workflow_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    # Document type key (e.g., "aadhaar_card", "pan_card")
    document_type_key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Display name (may be customized from the default)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    document_category: Mapped[DocumentCategory] = mapped_column(
        SAEnum(DocumentCategory), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # Criteria — natural language input from the client
    criteria_text: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Natural language criteria set by the client (e.g., 'must not be expired, name must match applicant')"
    )
    # Parsed logical criteria — structured representation derived from criteria_text
    # Format: {"conditions": [{"field": "expiry_date", "operator": "gt", "value": "today", ...}]}
    logical_criteria: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Additional metadata for the document
    allowed_formats: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, default=["jpg", "jpeg", "png", "pdf"]
    )
    max_file_size_mb: Mapped[int] = mapped_column(Integer, default=10)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="documents")

    def __repr__(self) -> str:
        return f"<WorkflowDocument id={self.id} type={self.document_type_key}>"


class WorkflowQuestion(Base):
    """
    A question to be asked to the customer during the verification session.
    """
    __tablename__ = "workflow_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType), nullable=False, default=QuestionType.TEXT
    )
    # For multiple_choice type
    options: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    # Context / helper text
    helper_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For validation — e.g., {"min": 0, "max": 100} for number types
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="questions")

    def __repr__(self) -> str:
        return f"<WorkflowQuestion id={self.id} type={self.question_type}>"


class WorkflowSession(Base):
    """
    A session represents one execution of a workflow for a specific customer.
    Initiated by the client, triggers the AI voice agent and WhatsApp channel.
    """
    __tablename__ = "workflow_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="RESTRICT"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Customer contact info
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Reference ID from the client's system (e.g., loan application ID)
    external_reference_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING
    )
    # Answers collected during the session
    question_answers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Summary of document collection status
    documents_status: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<WorkflowSession id={self.id} status={self.status}>"
