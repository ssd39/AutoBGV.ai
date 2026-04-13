# 05 — Frontend Guide

## Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5 (strict mode, zero errors)
- **Styling**: Tailwind CSS 3 with custom `brand` color palette
- **Animations**: Framer Motion 11
- **State**: Redux Toolkit 2 + React-Redux
- **Server State**: TanStack Query v5
- **HTTP Client**: Axios
- **Notifications**: react-hot-toast
- **Icons**: Lucide React
- **Port**: 3000

---

## Project Structure

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root HTML layout + Providers
│   ├── providers.tsx             # Redux + Query + Toast providers
│   ├── globals.css               # Tailwind base + custom component classes
│   └── (dashboard)/              # Route group — all authenticated pages
│       ├── layout.tsx            # Sidebar + Header wrapper (client component)
│       ├── page.tsx              # Dashboard home
│       ├── workflows/
│       │   ├── page.tsx          # Workflow list with search/filter/pagination
│       │   ├── create/page.tsx   # Workflow creation (4-step builder)
│       │   └── [id]/
│       │       ├── page.tsx      # Workflow detail view
│       │       └── edit/page.tsx # Edit workflow (loads into builder)
│       ├── sessions/page.tsx     # Session monitor (placeholder)
│       ├── analytics/page.tsx    # Analytics (placeholder)
│       └── settings/page.tsx     # Platform settings
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx           # Animated collapsible sidebar
│   │   └── Header.tsx            # Top header with search + actions
│   └── workflow/
│       ├── WorkflowBuilder.tsx   # Main builder with steps + tab switcher
│       ├── QuickStartTemplates.tsx  # Template gallery
│       └── builder/
│           ├── Step1BasicInfo.tsx   # Name, category, settings
│           ├── Step2Documents.tsx   # Document library + configured docs
│           ├── Step3Questions.tsx   # Question builder
│           └── Step4Review.tsx      # Review before save
│
├── store/
│   ├── index.ts                  # Store configuration + typed hooks
│   ├── workflowSlice.ts          # Workflows, builder state, async thunks
│   └── uiSlice.ts                # Sidebar, modals, notifications
│
├── lib/
│   ├── api.ts                    # Axios instance + all API calls
│   └── constants.ts              # Category configs, nav items, defaults
│
└── types/
    └── index.ts                  # All TypeScript interfaces and types
```

---

## Redux Store Shape

```typescript
{
  workflows: {
    // List state
    workflows: WorkflowSummary[]
    totalWorkflows: number
    isLoadingList: boolean
    listError: string | null

    // Detail state
    currentWorkflow: Workflow | null
    isLoadingWorkflow: boolean
    workflowError: string | null

    // Builder state (for create/edit)
    builder: {
      step: number              // 1–4
      name: string
      description: string
      category: WorkflowCategory
      welcome_message: string
      completion_message: string
      max_retry_attempts: number
      session_timeout_minutes: number
      documents: BuilderDocument[]
      questions: BuilderQuestion[]
      isSaving: boolean
      errors: Record<string, string>
    }

    // Document catalog
    documentCatalog: Record<string, DocumentTypeInfo[]>
    isCatalogLoaded: boolean

    // Templates
    templates: WorkflowTemplate[]
    isTemplatesLoaded: boolean
  },

  ui: {
    sidebarOpen: boolean
    activeModal: string | null
    modalData: Record<string, unknown> | null
    notifications: Notification[]
  }
}
```

---

## Key Redux Actions

### Workflow Actions
```typescript
// Async thunks
fetchWorkflows(params?)       // Load workflow list
fetchWorkflow(id)             // Load single workflow
createWorkflow()              // Save builder state as new workflow
activateWorkflow(id)          // Set workflow to active
duplicateWorkflow(id)         // Clone a workflow
deleteWorkflow(id)            // Delete a workflow
fetchDocumentCatalog()        // Load Indian document catalog
fetchTemplates()              // Load quick-start templates
createFromTemplate(key)       // Create workflow from template

// Sync actions
resetBuilder()                // Clear builder state
loadWorkflowIntoBuilder(wf)   // Pre-fill builder with existing workflow
setBuilderStep(n)             // Navigate wizard steps
setBuilderField(field, value) // Update any builder field
addBuilderDocument(doc)       // Add document to builder
updateBuilderDocument(_id, changes)
removeBuilderDocument(_id)
addBuilderQuestion(q)
updateBuilderQuestion(_id, changes)
removeBuilderQuestion(_id)
clearCurrentWorkflow()
```

---

## API Layer (`src/lib/api.ts`)

All API calls go through a single `workflowApi` object. The Next.js `next.config.js` rewrites proxy API calls:

```
/api/workflow/* → http://localhost:8001/api/v1/*
/api/agent/*    → http://localhost:8002/api/v1/*
/api/verify/*   → http://localhost:8003/api/v1/*
```

This means frontend code always uses relative URLs like `/api/workflow/workflows/`.

---

## Component Architecture

### WorkflowBuilder
The central component for creating and editing workflows.

```
WorkflowBuilder
├── Tab switcher (Scratch / Templates)
├── [Templates tab] → QuickStartTemplates
└── [Scratch tab]
    ├── Step Progress Indicator (steps 1-4)
    ├── [Step 1] Step1BasicInfo
    │   ├── Name input
    │   ├── Description textarea
    │   ├── Category grid selector
    │   └── Advanced settings (accordion)
    ├── [Step 2] Step2Documents
    │   ├── Left panel: Document Library
    │   │   ├── Search input
    │   │   ├── Category filter tabs
    │   │   └── Searchable document list (with OVI badge)
    │   └── Right panel: Configured Documents
    │       └── DocumentItem (expandable)
    │           ├── Display name
    │           ├── Required toggle
    │           ├── Criteria text (natural language)
    │           ├── Customer instructions
    │           └── File settings
    ├── [Step 3] Step3Questions
    │   ├── Suggested Questions grid
    │   └── Questions List
    │       └── QuestionItem (expandable)
    │           ├── Question text
    │           ├── Type selector (5 types)
    │           ├── Options manager (for MC)
    │           └── Required toggle
    └── [Step 4] Step4Review
        ├── Summary card
        ├── Documents list
        ├── Questions list
        ├── Settings summary
        └── Agent messages preview
```

---

## Tailwind Custom Components (globals.css)

```css
/* Buttons */
.btn           /* Base button */
.btn-primary   /* Indigo primary button */
.btn-secondary /* White outlined button */
.btn-danger    /* Red delete button */
.btn-ghost     /* Transparent hover button */
.btn-sm        /* Small size modifier */
.btn-lg        /* Large size modifier */

/* Cards */
.card          /* White rounded card with border */
.card-hover    /* Card with hover shadow effect */

/* Form */
.input         /* Standard text input */
.select        /* Dropdown select */
.textarea      /* Multi-line input */
.label         /* Form field label */

/* Other */
.badge         /* Rounded pill badge */
.sidebar-link  /* Nav item link */
.step-indicator /* Wizard step circle */
```

---

## Color Palette

```css
/* Brand (Indigo) */
brand-50  → #eef2ff
brand-100 → #e0e7ff
brand-500 → #6366f1
brand-600 → #4f46e5  /* Primary button background */
brand-700 → #4338ca
brand-900 → #312e81

/* Status colors */
draft    → gray
active   → green
inactive → yellow
archived → red
```

---

## Adding a New Page

1. Create `frontend/src/app/(dashboard)/your-page/page.tsx`
2. Add `'use client'` if using hooks/state
3. Add nav item to `Sidebar.tsx` (`navItems` array)
4. Page is automatically wrapped by the dashboard layout (Sidebar + Header)

---

## Adding a New API Endpoint to Frontend

1. Add the API call to `src/lib/api.ts` in the `workflowApi` object
2. Add async thunk in `src/store/workflowSlice.ts`
3. Handle pending/fulfilled/rejected in `extraReducers`
4. Use `useAppDispatch()` + `useAppSelector()` in components

---

## TypeScript Types (`src/types/index.ts`)

All domain types are in one file:
- `WorkflowStatus`, `WorkflowCategory`, `DocumentCategory`, `QuestionType`, `SessionStatus`
- `WorkflowDocument`, `WorkflowDocumentCreate`, `WorkflowDocumentUpdate`
- `WorkflowQuestion`, `WorkflowQuestionCreate`, `WorkflowQuestionUpdate`
- `Workflow`, `WorkflowSummary`, `WorkflowCreate`, `WorkflowUpdate`, `PaginatedWorkflows`
- `Session`, `SessionCreate`
- `DocumentTypeInfo`, `DocumentTypeCatalog`
- `WorkflowTemplate`
- `BuilderDocument`, `BuilderQuestion`, `WorkflowBuilderState` (UI-specific)
- `ApiError`
