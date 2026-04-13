// ─── Enums ────────────────────────────────────────────────────────────────────

export type WorkflowStatus = 'draft' | 'active' | 'inactive' | 'archived';
export type WorkflowCategory = 'kyc' | 'loan' | 'insurance' | 'background_check' | 'property' | 'business' | 'custom';
export type DocumentCategory = 'identity' | 'address' | 'income' | 'business' | 'property' | 'vehicle' | 'medical' | 'agriculture' | 'other';
export type QuestionType = 'text' | 'yes_no' | 'multiple_choice' | 'number' | 'date';
export type SessionStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'expired';

// ─── Criteria ─────────────────────────────────────────────────────────────────

export interface CriteriaCondition {
  field: string;
  operator: string;
  value: unknown;
  description: string;
}

export interface LogicalCriteria {
  raw_text: string;
  conditions: CriteriaCondition[];
  logic: 'AND' | 'OR';
}

// ─── Document Types ───────────────────────────────────────────────────────────

export interface DocumentTypeInfo {
  key: string;
  name: string;
  category: DocumentCategory;
  description: string;
  issuing_authority: string;
  is_ovi: boolean;
  is_opa: boolean;
  common_fields: string[];
}

export interface DocumentTypeCatalog {
  categories: Record<DocumentCategory, DocumentTypeInfo[]>;
  total: number;
}

// ─── Workflow Document ────────────────────────────────────────────────────────

export interface WorkflowDocument {
  id: string;
  workflow_id: string;
  document_type_key: string;
  display_name: string;
  document_category: DocumentCategory;
  description: string | null;
  is_required: boolean;
  order_index: number;
  criteria_text: string | null;
  logical_criteria: LogicalCriteria | null;
  allowed_formats: string[];
  max_file_size_mb: number;
  instructions: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDocumentCreate {
  document_type_key: string;
  display_name: string;
  document_category: DocumentCategory;
  description?: string;
  is_required: boolean;
  order_index: number;
  criteria_text?: string;
  logical_criteria?: LogicalCriteria;
  allowed_formats: string[];
  max_file_size_mb: number;
  instructions?: string;
}

export interface WorkflowDocumentUpdate {
  display_name?: string;
  description?: string;
  is_required?: boolean;
  order_index?: number;
  criteria_text?: string;
  logical_criteria?: LogicalCriteria;
  allowed_formats?: string[];
  max_file_size_mb?: number;
  instructions?: string;
}

// ─── Workflow Question ────────────────────────────────────────────────────────

export interface WorkflowQuestion {
  id: string;
  workflow_id: string;
  question_text: string;
  question_type: QuestionType;
  options: string[] | null;
  is_required: boolean;
  order_index: number;
  helper_text: string | null;
  validation_rules: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowQuestionCreate {
  question_text: string;
  question_type: QuestionType;
  options?: string[];
  is_required: boolean;
  order_index: number;
  helper_text?: string;
  validation_rules?: Record<string, unknown>;
}

export interface WorkflowQuestionUpdate {
  question_text?: string;
  question_type?: QuestionType;
  options?: string[];
  is_required?: boolean;
  order_index?: number;
  helper_text?: string;
  validation_rules?: Record<string, unknown>;
}

// ─── Workflow ─────────────────────────────────────────────────────────────────

export interface WorkflowSummary {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  category: WorkflowCategory;
  status: WorkflowStatus;
  is_template: boolean;
  template_key: string | null;
  document_count: number;
  question_count: number;
  session_count: number;
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  category: WorkflowCategory;
  status: WorkflowStatus;
  is_template: boolean;
  template_key: string | null;
  welcome_message: string | null;
  completion_message: string | null;
  max_retry_attempts: number;
  session_timeout_minutes: number;
  documents: WorkflowDocument[];
  questions: WorkflowQuestion[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  category: WorkflowCategory;
  status?: WorkflowStatus;
  welcome_message?: string;
  completion_message?: string;
  max_retry_attempts?: number;
  session_timeout_minutes?: number;
  documents: WorkflowDocumentCreate[];
  questions: WorkflowQuestionCreate[];
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  category?: WorkflowCategory;
  status?: WorkflowStatus;
  welcome_message?: string;
  completion_message?: string;
  max_retry_attempts?: number;
  session_timeout_minutes?: number;
}

export interface PaginatedWorkflows {
  items: WorkflowSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Agent Types ──────────────────────────────────────────────────────────────

export type AgentSessionStatus =
  | 'pending' | 'call_queued' | 'call_initiated' | 'call_ringing'
  | 'call_in_progress' | 'call_completed' | 'call_busy' | 'call_no_answer'
  | 'call_failed' | 'call_canceled' | 'interrupted';

export type AgentPhase = 'not_started' | 'collecting' | 'all_submitted' | 'complete';

export type VerificationStatus = 'requested' | 'pending' | 'passed' | 'failed';

export interface CallAttempt {
  call_sid: string;
  attempt_number: number;
  status: string | null;
  failure_reason: string | null;
  initiated_at: string | null;
  answered_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  stream_sid: string | null;
}

export interface AgentSession {
  session_id: string;
  workflow_id: string;
  client_id: string;
  customer_phone: string;
  customer_name: string | null;
  status: AgentSessionStatus;
  agent_phase: AgentPhase;
  attempt_count: number;
  call_sids: string[];
  current_call_sid: string | null;
  call_status: string | null;
  call_attempts: CallAttempt[];
  documents_status: Record<string, Record<string, unknown>>;
  verification_results: Record<string, VerificationStatus>;
  current_item_index: number;
  items_queue_length: number;
  question_answers: Record<string, string>;
  pending_upload_doc: string | null;
  failed_docs_requeue: string[];
  created_at: string;
  updated_at: string;
  session_started_at: string | null;
  session_ended_at: string | null;
}

export interface AgentSessionsResponse {
  sessions: AgentSession[];
  total: number;
}

// ─── Session ──────────────────────────────────────────────────────────────────

export interface Session {
  id: string;
  workflow_id: string;
  client_id: string;
  customer_name: string | null;
  customer_phone: string;
  customer_email: string | null;
  external_reference_id: string | null;
  status: SessionStatus;
  question_answers: Record<string, unknown> | null;
  documents_status: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  customer_name?: string;
  customer_phone: string;
  customer_email?: string;
  external_reference_id?: string;
}

// ─── Templates ────────────────────────────────────────────────────────────────

export interface WorkflowTemplate {
  template_key: string;
  name: string;
  description: string;
  category: WorkflowCategory;
  document_count: number;
  question_count: number;
}

// ─── UI Builder State ─────────────────────────────────────────────────────────

export interface BuilderDocument extends Omit<WorkflowDocumentCreate, 'order_index'> {
  _id: string; // local UUID before save
  order_index: number;
  _isNew?: boolean;
}

export interface BuilderQuestion extends Omit<WorkflowQuestionCreate, 'order_index'> {
  _id: string; // local UUID before save
  order_index: number;
  _isNew?: boolean;
}

export interface WorkflowBuilderState {
  step: number; // 1: basic info, 2: documents, 3: questions, 4: review
  name: string;
  description: string;
  category: WorkflowCategory;
  welcome_message: string;
  completion_message: string;
  max_retry_attempts: number;
  session_timeout_minutes: number;
  documents: BuilderDocument[];
  questions: BuilderQuestion[];
  isSaving: boolean;
  errors: Record<string, string>;
}

// ─── API Response ─────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[];
  status?: number;
}
