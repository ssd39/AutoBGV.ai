import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';
import {
  Workflow, WorkflowSummary, PaginatedWorkflows,
  WorkflowBuilderState, BuilderDocument, BuilderQuestion,
  WorkflowCategory, WorkflowStatus, DocumentCategory, QuestionType,
} from '@/types';
import { workflowApi } from '@/lib/api';

// ─── Initial Builder State ────────────────────────────────────────────────────

const initialBuilderState: WorkflowBuilderState = {
  step: 1,
  name: '',
  description: '',
  category: 'custom',
  welcome_message: '',
  completion_message: '',
  max_retry_attempts: 3,
  session_timeout_minutes: 60,
  documents: [],
  questions: [],
  isSaving: false,
  errors: {},
};

// ─── State ────────────────────────────────────────────────────────────────────

interface WorkflowState {
  // Workflow list
  workflows: WorkflowSummary[];
  totalWorkflows: number;
  currentPage: number;
  isLoadingList: boolean;
  listError: string | null;

  // Current workflow being viewed
  currentWorkflow: Workflow | null;
  isLoadingWorkflow: boolean;
  workflowError: string | null;

  // Builder (create/edit)
  builder: WorkflowBuilderState;

  // Catalog
  documentCatalog: Record<string, { key: string; name: string; category: string; description: string; issuing_authority: string; is_ovi: boolean; is_opa: boolean; common_fields: string[] }[]>;
  isCatalogLoaded: boolean;

  // Templates
  templates: { template_key: string; name: string; description: string; category: string; document_count: number; question_count: number }[];
  isTemplatesLoaded: boolean;
}

const initialState: WorkflowState = {
  workflows: [],
  totalWorkflows: 0,
  currentPage: 1,
  isLoadingList: false,
  listError: null,
  currentWorkflow: null,
  isLoadingWorkflow: false,
  workflowError: null,
  builder: initialBuilderState,
  documentCatalog: {},
  isCatalogLoaded: false,
  templates: [],
  isTemplatesLoaded: false,
};

// ─── Async Thunks ─────────────────────────────────────────────────────────────

export const fetchWorkflows = createAsyncThunk(
  'workflows/fetchAll',
  async (params: { page?: number; search?: string; category?: WorkflowCategory; status?: WorkflowStatus } = {}) => {
    return await workflowApi.list(params);
  }
);

export const fetchWorkflow = createAsyncThunk(
  'workflows/fetchOne',
  async (id: string) => {
    return await workflowApi.get(id);
  }
);

export const createWorkflow = createAsyncThunk(
  'workflows/create',
  async (_, { getState }) => {
    const state = (getState() as { workflows: WorkflowState }).workflows;
    const builder = state.builder;

    const payload = {
      name: builder.name,
      description: builder.description || undefined,
      category: builder.category,
      status: 'draft' as const,
      welcome_message: builder.welcome_message || undefined,
      completion_message: builder.completion_message || undefined,
      max_retry_attempts: builder.max_retry_attempts,
      session_timeout_minutes: builder.session_timeout_minutes,
      documents: builder.documents.map((d, i) => ({
        document_type_key: d.document_type_key,
        display_name: d.display_name,
        document_category: d.document_category,
        description: d.description,
        is_required: d.is_required,
        order_index: i,
        criteria_text: d.criteria_text,
        allowed_formats: d.allowed_formats,
        max_file_size_mb: d.max_file_size_mb,
        instructions: d.instructions,
      })),
      questions: builder.questions.map((q, i) => ({
        question_text: q.question_text,
        question_type: q.question_type,
        options: q.options,
        is_required: q.is_required,
        order_index: i,
        helper_text: q.helper_text,
        validation_rules: q.validation_rules,
      })),
    };
    return await workflowApi.create(payload);
  }
);

export const activateWorkflow = createAsyncThunk(
  'workflows/activate',
  async (id: string) => {
    return await workflowApi.activate(id);
  }
);

export const duplicateWorkflow = createAsyncThunk(
  'workflows/duplicate',
  async (id: string) => {
    return await workflowApi.duplicate(id);
  }
);

export const deleteWorkflow = createAsyncThunk(
  'workflows/delete',
  async (id: string) => {
    await workflowApi.delete(id);
    return id;
  }
);

export const fetchDocumentCatalog = createAsyncThunk(
  'workflows/fetchCatalog',
  async () => {
    return await workflowApi.getDocumentCatalog();
  }
);

export const fetchTemplates = createAsyncThunk(
  'workflows/fetchTemplates',
  async () => {
    return await workflowApi.getTemplates();
  }
);

export const createFromTemplate = createAsyncThunk(
  'workflows/createFromTemplate',
  async (templateKey: string) => {
    return await workflowApi.useTemplate(templateKey);
  }
);

// ─── Slice ────────────────────────────────────────────────────────────────────

const workflowSlice = createSlice({
  name: 'workflows',
  initialState,
  reducers: {
    // ─── Builder ──────────────────────────────────────────────────────────────

    resetBuilder: (state) => {
      state.builder = initialBuilderState;
    },

    loadWorkflowIntoBuilder: (state, action: PayloadAction<Workflow>) => {
      const wf = action.payload;
      state.builder = {
        step: 1,
        name: wf.name,
        description: wf.description || '',
        category: wf.category,
        welcome_message: wf.welcome_message || '',
        completion_message: wf.completion_message || '',
        max_retry_attempts: wf.max_retry_attempts,
        session_timeout_minutes: wf.session_timeout_minutes,
        documents: wf.documents.map((d) => ({
          _id: d.id,
          document_type_key: d.document_type_key,
          display_name: d.display_name,
          document_category: d.document_category,
          description: d.description || undefined,
          is_required: d.is_required,
          order_index: d.order_index,
          criteria_text: d.criteria_text || undefined,
          allowed_formats: d.allowed_formats || ['jpg', 'jpeg', 'png', 'pdf'],
          max_file_size_mb: d.max_file_size_mb,
          instructions: d.instructions || undefined,
        })),
        questions: wf.questions.map((q) => ({
          _id: q.id,
          question_text: q.question_text,
          question_type: q.question_type,
          options: q.options || undefined,
          is_required: q.is_required,
          order_index: q.order_index,
          helper_text: q.helper_text || undefined,
          validation_rules: q.validation_rules || undefined,
        })),
        isSaving: false,
        errors: {},
      };
    },

    setBuilderStep: (state, action: PayloadAction<number>) => {
      state.builder.step = action.payload;
    },

    setBuilderField: (state, action: PayloadAction<{ field: keyof WorkflowBuilderState; value: unknown }>) => {
      const { field, value } = action.payload;
      (state.builder as Record<string, unknown>)[field] = value;
    },

    // ─── Builder Documents ────────────────────────────────────────────────────

    addBuilderDocument: (state, action: PayloadAction<Omit<BuilderDocument, '_id'>>) => {
      state.builder.documents.push({
        ...action.payload,
        _id: uuidv4(),
        _isNew: true,
        order_index: state.builder.documents.length,
      });
    },

    updateBuilderDocument: (state, action: PayloadAction<{ _id: string; changes: Partial<BuilderDocument> }>) => {
      const { _id, changes } = action.payload;
      const idx = state.builder.documents.findIndex((d) => d._id === _id);
      if (idx !== -1) {
        state.builder.documents[idx] = { ...state.builder.documents[idx], ...changes };
      }
    },

    removeBuilderDocument: (state, action: PayloadAction<string>) => {
      state.builder.documents = state.builder.documents
        .filter((d) => d._id !== action.payload)
        .map((d, i) => ({ ...d, order_index: i }));
    },

    reorderBuilderDocuments: (state, action: PayloadAction<BuilderDocument[]>) => {
      state.builder.documents = action.payload.map((d, i) => ({ ...d, order_index: i }));
    },

    // ─── Builder Questions ────────────────────────────────────────────────────

    addBuilderQuestion: (state, action: PayloadAction<Omit<BuilderQuestion, '_id'>>) => {
      state.builder.questions.push({
        ...action.payload,
        _id: uuidv4(),
        _isNew: true,
        order_index: state.builder.questions.length,
      });
    },

    updateBuilderQuestion: (state, action: PayloadAction<{ _id: string; changes: Partial<BuilderQuestion> }>) => {
      const { _id, changes } = action.payload;
      const idx = state.builder.questions.findIndex((q) => q._id === _id);
      if (idx !== -1) {
        state.builder.questions[idx] = { ...state.builder.questions[idx], ...changes };
      }
    },

    removeBuilderQuestion: (state, action: PayloadAction<string>) => {
      state.builder.questions = state.builder.questions
        .filter((q) => q._id !== action.payload)
        .map((q, i) => ({ ...q, order_index: i }));
    },

    clearCurrentWorkflow: (state) => {
      state.currentWorkflow = null;
      state.workflowError = null;
    },

    setBuilderError: (state, action: PayloadAction<{ field: string; message: string }>) => {
      state.builder.errors[action.payload.field] = action.payload.message;
    },

    clearBuilderErrors: (state) => {
      state.builder.errors = {};
    },
  },

  extraReducers: (builder) => {
    // Fetch all
    builder
      .addCase(fetchWorkflows.pending, (state) => {
        state.isLoadingList = true;
        state.listError = null;
      })
      .addCase(fetchWorkflows.fulfilled, (state, action) => {
        state.isLoadingList = false;
        state.workflows = action.payload.items;
        state.totalWorkflows = action.payload.total;
      })
      .addCase(fetchWorkflows.rejected, (state, action) => {
        state.isLoadingList = false;
        state.listError = action.error.message || 'Failed to load workflows';
      });

    // Fetch one
    builder
      .addCase(fetchWorkflow.pending, (state) => {
        state.isLoadingWorkflow = true;
        state.workflowError = null;
      })
      .addCase(fetchWorkflow.fulfilled, (state, action) => {
        state.isLoadingWorkflow = false;
        state.currentWorkflow = action.payload;
      })
      .addCase(fetchWorkflow.rejected, (state, action) => {
        state.isLoadingWorkflow = false;
        state.workflowError = action.error.message || 'Failed to load workflow';
      });

    // Create
    builder
      .addCase(createWorkflow.pending, (state) => {
        state.builder.isSaving = true;
      })
      .addCase(createWorkflow.fulfilled, (state, action) => {
        state.builder.isSaving = false;
        state.currentWorkflow = action.payload;
      })
      .addCase(createWorkflow.rejected, (state, action) => {
        state.builder.isSaving = false;
        state.builder.errors['_save'] = action.error.message || 'Failed to save workflow';
      });

    // Activate
    builder.addCase(activateWorkflow.fulfilled, (state, action) => {
      state.currentWorkflow = action.payload;
      const idx = state.workflows.findIndex((w) => w.id === action.payload.id);
      if (idx !== -1) state.workflows[idx].status = 'active';
    });

    // Delete
    builder.addCase(deleteWorkflow.fulfilled, (state, action) => {
      state.workflows = state.workflows.filter((w) => w.id !== action.payload);
    });

    // Catalog
    builder.addCase(fetchDocumentCatalog.fulfilled, (state, action) => {
      state.documentCatalog = action.payload.categories as unknown as typeof state.documentCatalog;
      state.isCatalogLoaded = true;
    });

    // Templates
    builder.addCase(fetchTemplates.fulfilled, (state, action) => {
      state.templates = action.payload.templates;
      state.isTemplatesLoaded = true;
    });

    // Create from template
    builder.addCase(createFromTemplate.fulfilled, (state, action) => {
      state.currentWorkflow = action.payload;
    });
  },
});

export const {
  resetBuilder, loadWorkflowIntoBuilder, setBuilderStep, setBuilderField,
  addBuilderDocument, updateBuilderDocument, removeBuilderDocument, reorderBuilderDocuments,
  addBuilderQuestion, updateBuilderQuestion, removeBuilderQuestion,
  clearCurrentWorkflow, setBuilderError, clearBuilderErrors,
} = workflowSlice.actions;

export default workflowSlice.reducer;
