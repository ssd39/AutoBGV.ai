# 04 — API Reference

## Base URL
```
Workflow Service: http://localhost:8001/api/v1
Agent Service:   http://localhost:8002/api/v1  (stub)
Verify Service:  http://localhost:8003/api/v1  (stub)
```

Interactive docs: `http://localhost:8001/docs` (Swagger UI)

---

## Authentication
> Phase 1: No authentication required. `client_id` defaults to `client_001`.
> Phase 4: JWT Bearer token will be required.

---

## Workflow Endpoints

### `POST /workflows/`
Create a new workflow.

**Request body:**
```json
{
  "name": "Home Loan KYC",
  "description": "KYC for home loan applicants",
  "category": "loan",
  "status": "draft",
  "welcome_message": "Hello! I'm calling to collect documents for your home loan.",
  "completion_message": "Thank you! Documents submitted successfully.",
  "max_retry_attempts": 3,
  "session_timeout_minutes": 60,
  "documents": [
    {
      "document_type_key": "aadhaar_card",
      "display_name": "Aadhaar Card",
      "document_category": "identity",
      "is_required": true,
      "criteria_text": "Must not be expired. Name must match applicant.",
      "allowed_formats": ["jpg", "jpeg", "png", "pdf"],
      "max_file_size_mb": 10
    }
  ],
  "questions": [
    {
      "question_text": "What is your employment type?",
      "question_type": "multiple_choice",
      "options": ["Salaried", "Self-Employed"],
      "is_required": true,
      "order_index": 0
    }
  ]
}
```

**Response:** `201 Created` → Full `WorkflowResponse`

---

### `GET /workflows/`
List all workflows with pagination and filters.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `category` | string | Filter by category |
| `status` | string | Filter by status |
| `search` | string | Search by name or description |

**Response:** `200 OK`
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

### `GET /workflows/{workflow_id}`
Get full workflow details including documents and questions.

**Response:** `200 OK` → Full `WorkflowResponse`

---

### `PATCH /workflows/{workflow_id}`
Update workflow metadata (name, description, settings).
> Does NOT update documents/questions — use separate endpoints.

**Request body** (all fields optional):
```json
{
  "name": "Updated Name",
  "status": "active",
  "max_retry_attempts": 5
}
```

---

### `DELETE /workflows/{workflow_id}`
Delete workflow and all associated documents, questions. Sessions are preserved.

**Response:** `204 No Content`

---

### `POST /workflows/{workflow_id}/activate`
Activate a draft workflow (must have at least 1 document).

**Response:** `200 OK` → Updated `WorkflowResponse`

---

### `POST /workflows/{workflow_id}/duplicate`
Create a copy of an existing workflow (copy is in `draft` status).

**Response:** `201 Created` → New `WorkflowResponse`

---

## Document Endpoints

### `POST /workflows/{workflow_id}/documents`
Add a document requirement to a workflow.

**Request body:** `WorkflowDocumentCreate`

**Response:** `201 Created` → `WorkflowDocumentResponse`

---

### `PATCH /workflows/{workflow_id}/documents/{document_id}`
Update a document requirement (criteria, name, required flag, etc.).

---

### `DELETE /workflows/{workflow_id}/documents/{document_id}`
Remove a document from the workflow.

**Response:** `204 No Content`

---

## Question Endpoints

### `POST /workflows/{workflow_id}/questions`
Add a question to a workflow.

**Request body:**
```json
{
  "question_text": "Are you a PEP?",
  "question_type": "yes_no",
  "is_required": true,
  "order_index": 0
}
```

---

### `PATCH /workflows/{workflow_id}/questions/{question_id}`
Update question text, type, or options.

---

### `DELETE /workflows/{workflow_id}/questions/{question_id}`
Remove a question from the workflow.

---

## Session Endpoints

### `POST /workflows/{workflow_id}/sessions`
Initiate a new session for a customer. Workflow must be `active`.

**Request body:**
```json
{
  "customer_name": "Rahul Sharma",
  "customer_phone": "+919876543210",
  "customer_email": "rahul@example.com",
  "external_reference_id": "LOAN-2024-001"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "workflow_id": "uuid",
  "client_id": "client_001",
  "customer_phone": "+919876543210",
  "status": "pending",
  "expires_at": "2026-04-13T11:00:00Z",
  "created_at": "2026-04-13T10:00:00Z"
}
```

---

### `GET /workflows/{workflow_id}/sessions`
List sessions for a workflow.

**Query params:** `page`, `page_size`

---

## Template Endpoints

### `GET /workflows/templates/list`
List all available quick-start templates.

**Response:**
```json
{
  "templates": [
    {
      "template_key": "basic_individual_kyc",
      "name": "Basic Individual KYC",
      "description": "Standard KYC per RBI directions",
      "category": "kyc",
      "document_count": 3,
      "question_count": 3
    }
  ]
}
```

---

### `POST /workflows/templates/{template_key}/use`
Create a new workflow from a quick-start template.

**Template keys available:**
- `basic_individual_kyc`
- `home_loan_kyc`
- `insurance_claim`
- `business_kyc`
- `vehicle_loan_kyc`
- `employment_bgv`

**Request body** (optional overrides):
```json
{
  "name": "My Custom Loan KYC"
}
```

**Response:** `201 Created` → `WorkflowResponse`

---

## Catalog Endpoint

### `GET /workflows/catalog/documents`
Get the complete Indian document catalog grouped by category.

**Response:**
```json
{
  "categories": {
    "identity": [
      {
        "key": "aadhaar_card",
        "name": "Aadhaar Card",
        "category": "identity",
        "description": "12-digit unique identification...",
        "issuing_authority": "UIDAI",
        "is_ovi": true,
        "is_opa": true,
        "common_fields": ["aadhaar_number", "name", "dob", "address", "photo"]
      }
    ],
    "address": [...],
    "income": [...]
  },
  "total": 52
}
```

---

## Criteria Parsing Endpoint

### `POST /workflows/criteria/parse`
Convert natural language criteria to structured logical conditions.

**Request body:**
```json
{
  "criteria_text": "Must not be expired. Name must match applicant. Both sides required.",
  "document_type_key": "aadhaar_card"
}
```

**Response:**
```json
{
  "criteria_text": "Must not be expired. Name must match applicant. Both sides required.",
  "logical_criteria": {
    "raw_text": "Must not be expired...",
    "conditions": [
      {"field": "expiry_date", "operator": "gt", "value": "today", "description": "Document must not be expired"},
      {"field": "name_match", "operator": "eq", "value": "applicant_name", "description": "Name must match"},
      {"field": "both_sides_provided", "operator": "eq", "value": true, "description": "Both sides required"}
    ],
    "logic": "AND"
  },
  "confidence": 0.75
}
```

---

## Health Check

### `GET /health`
```json
{
  "status": "healthy",
  "service": "workflow-service",
  "version": "0.1.0",
  "environment": "development"
}
```

---

## Error Responses

All errors follow FastAPI's standard format:
```json
{
  "detail": "Workflow abc-123 not found"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request / validation error |
| `404` | Resource not found |
| `422` | Pydantic validation error |
| `500` | Internal server error |

---

## Pydantic Models (Key)

### `WorkflowResponse`
```python
class WorkflowResponse(BaseModel):
    id: UUID
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
    documents: list[WorkflowDocumentResponse]
    questions: list[WorkflowQuestionResponse]
    created_at: datetime
    updated_at: datetime
```
