import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  Workflow, WorkflowCreate, WorkflowUpdate, WorkflowSummary,
  PaginatedWorkflows, WorkflowDocument, WorkflowDocumentCreate,
  WorkflowDocumentUpdate, WorkflowQuestion, WorkflowQuestionCreate,
  WorkflowQuestionUpdate, Session, SessionCreate, WorkflowTemplate,
  DocumentTypeCatalog, WorkflowCategory, WorkflowStatus,
  AgentSession, AgentSessionsResponse,
} from '@/types';

const BASE_URL = typeof window !== 'undefined'
  ? ''  // Use Next.js rewrite proxies on the client
  : (process.env.NEXT_PUBLIC_WORKFLOW_SERVICE_URL || 'http://localhost:8001');

// ─── Axios instance ───────────────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor — could add auth headers here in future
api.interceptors.request.use((config) => {
  return config;
});

// Response interceptor — normalize errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const detail = (error.response?.data as { detail?: string })?.detail;
    const message = typeof detail === 'string' ? detail : error.message;
    return Promise.reject(new Error(message || 'An unexpected error occurred'));
  }
);

// ─── Workflow API ─────────────────────────────────────────────────────────────

export const workflowApi = {
  // List workflows
  list: async (params?: {
    page?: number;
    page_size?: number;
    category?: WorkflowCategory;
    status?: WorkflowStatus;
    search?: string;
  }): Promise<PaginatedWorkflows> => {
    const response = await api.get('/api/workflow/workflows/', { params });
    return response.data;
  },

  // Get single workflow
  get: async (id: string): Promise<Workflow> => {
    const response = await api.get(`/api/workflow/workflows/${id}`);
    return response.data;
  },

  // Create workflow
  create: async (data: WorkflowCreate): Promise<Workflow> => {
    const response = await api.post('/api/workflow/workflows/', data);
    return response.data;
  },

  // Update workflow
  update: async (id: string, data: WorkflowUpdate): Promise<Workflow> => {
    const response = await api.patch(`/api/workflow/workflows/${id}`, data);
    return response.data;
  },

  // Delete workflow
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/workflow/workflows/${id}`);
  },

  // Activate workflow
  activate: async (id: string): Promise<Workflow> => {
    const response = await api.post(`/api/workflow/workflows/${id}/activate`);
    return response.data;
  },

  // Duplicate workflow
  duplicate: async (id: string): Promise<Workflow> => {
    const response = await api.post(`/api/workflow/workflows/${id}/duplicate`);
    return response.data;
  },

  // ─── Documents ──────────────────────────────────────────────────────────────

  addDocument: async (workflowId: string, data: WorkflowDocumentCreate): Promise<WorkflowDocument> => {
    const response = await api.post(`/api/workflow/workflows/${workflowId}/documents`, data);
    return response.data;
  },

  updateDocument: async (workflowId: string, documentId: string, data: WorkflowDocumentUpdate): Promise<WorkflowDocument> => {
    const response = await api.patch(`/api/workflow/workflows/${workflowId}/documents/${documentId}`, data);
    return response.data;
  },

  removeDocument: async (workflowId: string, documentId: string): Promise<void> => {
    await api.delete(`/api/workflow/workflows/${workflowId}/documents/${documentId}`);
  },

  // ─── Questions ──────────────────────────────────────────────────────────────

  addQuestion: async (workflowId: string, data: WorkflowQuestionCreate): Promise<WorkflowQuestion> => {
    const response = await api.post(`/api/workflow/workflows/${workflowId}/questions`, data);
    return response.data;
  },

  updateQuestion: async (workflowId: string, questionId: string, data: WorkflowQuestionUpdate): Promise<WorkflowQuestion> => {
    const response = await api.patch(`/api/workflow/workflows/${workflowId}/questions/${questionId}`, data);
    return response.data;
  },

  removeQuestion: async (workflowId: string, questionId: string): Promise<void> => {
    await api.delete(`/api/workflow/workflows/${workflowId}/questions/${questionId}`);
  },

  // ─── Sessions ───────────────────────────────────────────────────────────────

  createSession: async (workflowId: string, data: SessionCreate): Promise<Session> => {
    const response = await api.post(`/api/workflow/workflows/${workflowId}/sessions`, data);
    return response.data;
  },

  getSessions: async (workflowId: string, page = 1, pageSize = 20) => {
    const response = await api.get(`/api/workflow/workflows/${workflowId}/sessions`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // ─── Templates ──────────────────────────────────────────────────────────────

  getTemplates: async (): Promise<{ templates: WorkflowTemplate[] }> => {
    const response = await api.get('/api/workflow/workflows/templates/list');
    return response.data;
  },

  useTemplate: async (templateKey: string, overrides?: Partial<WorkflowCreate>): Promise<Workflow> => {
    const response = await api.post(
      `/api/workflow/workflows/templates/${templateKey}/use`,
      overrides || null
    );
    return response.data;
  },

  // ─── Document Catalog ────────────────────────────────────────────────────────

  getDocumentCatalog: async (): Promise<DocumentTypeCatalog> => {
    const response = await api.get('/api/workflow/workflows/catalog/documents');
    return response.data;
  },

  // ─── Criteria Parsing ────────────────────────────────────────────────────────

  parseCriteria: async (criteriaText: string, documentTypeKey: string) => {
    const response = await api.post('/api/workflow/workflows/criteria/parse', {
      criteria_text: criteriaText,
      document_type_key: documentTypeKey,
    });
    return response.data;
  },
};

// ─── Agent API ────────────────────────────────────────────────────────────────
// Proxied via Next.js rewrite: /api/agent/* → http://localhost:8002/api/v1/*

export const agentApi = {
  // List all active sessions from agent in-process cache
  listSessions: async (): Promise<AgentSessionsResponse> => {
    const response = await api.get('/api/agent/sessions');
    return response.data;
  },

  // Get a single session by ID
  getSession: async (sessionId: string): Promise<AgentSession> => {
    const response = await api.get(`/api/agent/sessions/${sessionId}`);
    return response.data;
  },

  // Manually trigger an outbound call for an existing session
  initiateCall: async (sessionId: string) => {
    const response = await api.post('/api/agent/calls/initiate', { session_id: sessionId });
    return response.data;
  },

  // Force-close a session (interrupt + DB sync)
  interruptSession: async (sessionId: string) => {
    const response = await api.post(`/api/agent/sessions/${sessionId}/interrupt`);
    return response.data;
  },

  // Dev: simulate a customer document upload (no Twilio required)
  simulateDocUpload: async (sessionId: string, documentKey: string) => {
    const response = await api.post(`/api/agent/sessions/${sessionId}/document-uploaded`, {
      document_key: documentKey,
    });
    return response.data;
  },

  // Dev: inject a message directly into the live Deepgram agent session
  injectMessage: async (sessionId: string, message: string) => {
    const response = await api.post(`/api/agent/sessions/${sessionId}/inject-message`, { message });
    return response.data;
  },

  // Get a pre-signed S3 download URL for an uploaded WhatsApp document
  getMediaDownloadUrl: async (
    sessionId: string,
    docKey: string,
    expiry = 3600,
  ): Promise<{ download_url: string; expires_in: number; doc_key: string; session_id: string }> => {
    const response = await api.get(
      `/api/agent/sessions/${sessionId}/media/${encodeURIComponent(docKey)}/download`,
      { params: { expiry } },
    );
    return response.data;
  },
};

// ─── Verify API ───────────────────────────────────────────────────────────────
// Proxied via Next.js rewrite: /api/verify/* → http://localhost:8003/api/v1/*

export const verifyApi = {
  // Dev: publish a fabricated pass/fail result (no OCR required)
  mockResult: async (
    sessionId: string,
    documentKey: string,
    passed: boolean,
    reason = '',
  ) => {
    const response = await api.post('/api/verify/verify/mock-result', {
      session_id: sessionId,
      document_key: documentKey,
      passed,
      reason,
    });
    return response.data;
  },
};

export default api;
