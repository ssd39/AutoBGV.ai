# 03 — Database Schema

## Overview

**Database**: PostgreSQL 16  
**ORM**: SQLAlchemy 2.0 (async)  
**Migrations**: Alembic  
**Primary keys**: UUID v4 throughout  
**Timestamps**: All tables have `created_at` and `updated_at` with timezone

---

## Entity Relationship

```
┌──────────────────┐       ┌──────────────────────┐
│     workflows    │──────<│   workflow_documents  │
│                  │       └──────────────────────┘
│  id (PK)         │
│  client_id       │       ┌──────────────────────┐
│  name            │──────<│   workflow_questions  │
│  description     │       └──────────────────────┘
│  category        │
│  status          │       ┌──────────────────────┐
│  is_template     │──────<│   workflow_sessions   │
│  template_key    │       └──────────────────────┘
│  welcome_message │
│  completion_msg  │
│  max_retries     │
│  timeout_mins    │
│  created_at      │
│  updated_at      │
└──────────────────┘
```

---

## Tables

### `workflows`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Primary key |
| `client_id` | VARCHAR(100) | NOT NULL, INDEX | Client identifier |
| `name` | VARCHAR(200) | NOT NULL | Workflow display name |
| `description` | TEXT | NULLABLE | Optional description |
| `category` | ENUM | NOT NULL | `kyc`, `loan`, `insurance`, `background_check`, `property`, `business`, `custom` |
| `status` | ENUM | NOT NULL, default `draft` | `draft`, `active`, `inactive`, `archived` |
| `is_template` | BOOLEAN | default false | Whether this is a system template |
| `template_key` | VARCHAR(100) | NULLABLE | e.g. `basic_individual_kyc` |
| `welcome_message` | TEXT | NULLABLE | AI agent greeting message |
| `completion_message` | TEXT | NULLABLE | AI agent closing message |
| `max_retry_attempts` | INTEGER | default 3 | Max doc upload retries |
| `session_timeout_minutes` | INTEGER | default 60 | Session expiry |
| `created_at` | TIMESTAMPTZ | NOT NULL, server_default | Creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto-update | Last update time |

**Indexes**: `client_id`

---

### `workflow_documents`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Primary key |
| `workflow_id` | UUID | FK → workflows.id (CASCADE DELETE) | Parent workflow |
| `document_type_key` | VARCHAR(100) | NOT NULL | e.g. `aadhaar_card`, `pan_card` |
| `display_name` | VARCHAR(200) | NOT NULL | Client-customizable name |
| `document_category` | ENUM | NOT NULL | `identity`, `address`, `income`, `business`, `property`, `vehicle`, `medical`, `agriculture`, `other` |
| `description` | TEXT | NULLABLE | Optional description |
| `is_required` | BOOLEAN | default true | Required vs optional |
| `order_index` | INTEGER | default 0 | Display order |
| `criteria_text` | TEXT | NULLABLE | Natural language criteria |
| `logical_criteria` | JSONB | NULLABLE | Parsed logical conditions |
| `allowed_formats` | JSONB | default `["jpg","jpeg","png","pdf"]` | File formats |
| `max_file_size_mb` | INTEGER | default 10 | Max upload size |
| `instructions` | TEXT | NULLABLE | Customer-facing instructions |
| `created_at` | TIMESTAMPTZ | NOT NULL | Creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last update time |

**`logical_criteria` JSONB structure:**
```json
{
  "raw_text": "Must not be expired. Name must match applicant.",
  "conditions": [
    {
      "field": "expiry_date",
      "operator": "gt",
      "value": "today",
      "description": "Document must not be expired"
    },
    {
      "field": "name_match",
      "operator": "eq",
      "value": "applicant_name",
      "description": "Name on document must match applicant name"
    }
  ],
  "logic": "AND"
}
```

---

### `workflow_questions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Primary key |
| `workflow_id` | UUID | FK → workflows.id (CASCADE DELETE) | Parent workflow |
| `question_text` | TEXT | NOT NULL | The question to ask |
| `question_type` | ENUM | NOT NULL | `text`, `yes_no`, `multiple_choice`, `number`, `date` |
| `options` | JSONB | NULLABLE | Options for `multiple_choice` type |
| `is_required` | BOOLEAN | default true | Required vs optional |
| `order_index` | INTEGER | default 0 | Display order |
| `helper_text` | TEXT | NULLABLE | Additional context |
| `validation_rules` | JSONB | NULLABLE | e.g. `{"min": 0, "max": 100}` for numbers |
| `created_at` | TIMESTAMPTZ | NOT NULL | Creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last update time |

---

### `workflow_sessions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Primary key |
| `workflow_id` | UUID | FK → workflows.id (RESTRICT DELETE) | Workflow being executed |
| `client_id` | VARCHAR(100) | NOT NULL, INDEX | Client who initiated |
| `customer_name` | VARCHAR(200) | NULLABLE | Customer's name |
| `customer_phone` | VARCHAR(20) | NOT NULL | Customer's phone (for AI call) |
| `customer_email` | VARCHAR(200) | NULLABLE | Customer's email |
| `external_reference_id` | VARCHAR(200) | NULLABLE, INDEX | Client's internal ref (loan ID, etc.) |
| `status` | ENUM | NOT NULL, default `pending` | `pending`, `in_progress`, `completed`, `failed`, `expired` |
| `question_answers` | JSONB | NULLABLE | Map of question_id → answer |
| `documents_status` | JSONB | NULLABLE | Map of doc_type_key → status |
| `started_at` | TIMESTAMPTZ | NULLABLE | When AI call started |
| `completed_at` | TIMESTAMPTZ | NULLABLE | When session completed |
| `expires_at` | TIMESTAMPTZ | NULLABLE | Expiry time |
| `created_at` | TIMESTAMPTZ | NOT NULL | Creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Last update time |

**`documents_status` JSONB structure (Phase 2):**
```json
{
  "aadhaar_card": {
    "status": "verified",
    "uploaded_at": "2026-04-13T10:00:00Z",
    "verified_at": "2026-04-13T10:01:00Z",
    "s3_path": "client_001/session-uuid/aadhaar_card/front.pdf",
    "criteria_results": [
      {"field": "expiry_date", "passed": true},
      {"field": "name_match", "passed": true}
    ]
  },
  "pan_card": {
    "status": "failed",
    "failure_reason": "Photo not clearly visible",
    "retry_count": 1
  }
}
```

---

## Enums

### `WorkflowStatus`
```python
draft     # Being configured, not accepting sessions
active    # Accepting sessions
inactive  # Temporarily paused
archived  # Permanently disabled
```

### `WorkflowCategory`
```python
kyc, loan, insurance, background_check, property, business, custom
```

### `DocumentCategory`
```python
identity, address, income, business, property, vehicle, medical, agriculture, other
```

### `QuestionType`
```python
text, yes_no, multiple_choice, number, date
```

### `SessionStatus`
```python
pending     # Created but AI call not started
in_progress # AI call active, collecting docs
completed   # All documents verified
failed      # Max retries exceeded or error
expired     # Session timeout reached
```

---

## SQLAlchemy Models Location

```
services/workflow/app/models/workflow.py
```

## Alembic Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Migration files are in: `services/workflow/alembic/versions/`

> **Note**: In development mode (`ENVIRONMENT=development`), tables are auto-created via `Base.metadata.create_all()` on startup. Use Alembic for production deployments.
