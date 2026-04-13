import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { AgentSession } from '@/types';
import { agentApi, verifyApi } from '@/lib/api';

// ─── State ────────────────────────────────────────────────────────────────────

interface SessionState {
  sessions: AgentSession[];
  total: number;
  isLoading: boolean;
  error: string | null;
  selectedSessionId: string | null;
  lastFetchedAt: string | null;
  // Per-session action loading
  actionLoading: Record<string, boolean>;
}

const initialState: SessionState = {
  sessions: [],
  total: 0,
  isLoading: false,
  error: null,
  selectedSessionId: null,
  lastFetchedAt: null,
  actionLoading: {},
};

// ─── Async Thunks ─────────────────────────────────────────────────────────────

export const fetchAgentSessions = createAsyncThunk(
  'sessions/fetchAll',
  async () => {
    return await agentApi.listSessions();
  }
);

export const fetchAgentSession = createAsyncThunk(
  'sessions/fetchOne',
  async (sessionId: string) => {
    return await agentApi.getSession(sessionId);
  }
);

export const initiateCall = createAsyncThunk(
  'sessions/initiateCall',
  async (sessionId: string) => {
    const result = await agentApi.initiateCall(sessionId);
    return { sessionId, result };
  }
);

export const interruptSession = createAsyncThunk(
  'sessions/interrupt',
  async (sessionId: string) => {
    const result = await agentApi.interruptSession(sessionId);
    return { sessionId, result };
  }
);

export const simulateDocUpload = createAsyncThunk(
  'sessions/simulateUpload',
  async ({ sessionId, documentKey }: { sessionId: string; documentKey: string }) => {
    const result = await agentApi.simulateDocUpload(sessionId, documentKey);
    return { sessionId, documentKey, result };
  }
);

export const mockVerifyResult = createAsyncThunk(
  'sessions/mockVerify',
  async ({
    sessionId,
    documentKey,
    passed,
    reason,
  }: {
    sessionId: string;
    documentKey: string;
    passed: boolean;
    reason?: string;
  }) => {
    const result = await verifyApi.mockResult(sessionId, documentKey, passed, reason);
    return { sessionId, documentKey, passed, result };
  }
);

// ─── Slice ────────────────────────────────────────────────────────────────────

const sessionSlice = createSlice({
  name: 'sessions',
  initialState,
  reducers: {
    selectSession: (state, action: PayloadAction<string | null>) => {
      state.selectedSessionId = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    // Optimistically update a session after an action
    updateSession: (state, action: PayloadAction<AgentSession>) => {
      const idx = state.sessions.findIndex((s) => s.session_id === action.payload.session_id);
      if (idx !== -1) {
        state.sessions[idx] = action.payload;
      } else {
        state.sessions.unshift(action.payload);
        state.total += 1;
      }
    },
  },

  extraReducers: (builder) => {
    // Fetch all sessions
    builder
      .addCase(fetchAgentSessions.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchAgentSessions.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sessions = action.payload.sessions;
        state.total = action.payload.total;
        state.lastFetchedAt = new Date().toISOString();
      })
      .addCase(fetchAgentSessions.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch sessions';
      });

    // Fetch single session — updates the session in the list
    builder.addCase(fetchAgentSession.fulfilled, (state, action) => {
      const idx = state.sessions.findIndex((s) => s.session_id === action.payload.session_id);
      if (idx !== -1) {
        state.sessions[idx] = action.payload;
      } else {
        state.sessions.unshift(action.payload);
        state.total += 1;
      }
    });

    // Initiate call
    builder
      .addCase(initiateCall.pending, (state, action) => {
        state.actionLoading[action.meta.arg] = true;
      })
      .addCase(initiateCall.fulfilled, (state, action) => {
        state.actionLoading[action.payload.sessionId] = false;
      })
      .addCase(initiateCall.rejected, (state, action) => {
        state.actionLoading[action.meta.arg] = false;
      });

    // Interrupt session
    builder
      .addCase(interruptSession.pending, (state, action) => {
        state.actionLoading[`interrupt-${action.meta.arg}`] = true;
      })
      .addCase(interruptSession.fulfilled, (state, action) => {
        state.actionLoading[`interrupt-${action.payload.sessionId}`] = false;
        // Mark session as interrupted in local state
        const idx = state.sessions.findIndex((s) => s.session_id === action.payload.sessionId);
        if (idx !== -1) {
          state.sessions[idx].status = 'interrupted';
        }
      })
      .addCase(interruptSession.rejected, (state, action) => {
        state.actionLoading[`interrupt-${action.meta.arg}`] = false;
      });

    // Simulate doc upload
    builder
      .addCase(simulateDocUpload.pending, (state, action) => {
        state.actionLoading[`upload-${action.meta.arg.sessionId}-${action.meta.arg.documentKey}`] = true;
      })
      .addCase(simulateDocUpload.fulfilled, (state, action) => {
        state.actionLoading[`upload-${action.payload.sessionId}-${action.payload.documentKey}`] = false;
      })
      .addCase(simulateDocUpload.rejected, (state, action) => {
        state.actionLoading[`upload-${action.meta.arg.sessionId}-${action.meta.arg.documentKey}`] = false;
      });

    // Mock verify result
    builder
      .addCase(mockVerifyResult.pending, (state, action) => {
        state.actionLoading[`verify-${action.meta.arg.sessionId}-${action.meta.arg.documentKey}`] = true;
      })
      .addCase(mockVerifyResult.fulfilled, (state, action) => {
        state.actionLoading[`verify-${action.payload.sessionId}-${action.payload.documentKey}`] = false;
      })
      .addCase(mockVerifyResult.rejected, (state, action) => {
        state.actionLoading[`verify-${action.meta.arg.sessionId}-${action.meta.arg.documentKey}`] = false;
      });
  },
});

export const { selectSession, clearError, updateSession } = sessionSlice.actions;
export default sessionSlice.reducer;
