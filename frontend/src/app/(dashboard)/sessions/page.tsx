'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
  Play, Clock, CheckCircle, XCircle, PhoneCall, RefreshCw,
  ChevronDown, ChevronUp, Phone, AlertCircle, Loader2,
  Upload, ShieldCheck, ShieldX, MessageSquare, FileText,
  HelpCircle, StopCircle, Activity, Zap, Timer, Download,
} from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { agentApi } from '@/lib/api';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchAgentSessions, fetchAgentSession, initiateCall,
  interruptSession, simulateDocUpload, mockVerifyResult, selectSession,
} from '@/store/sessionSlice';
import { AgentSession, AgentSessionStatus } from '@/types';

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<AgentSessionStatus, { label: string; color: string; bg: string; dot: string }> = {
  pending:          { label: 'Pending',       color: 'text-gray-600',   bg: 'bg-gray-100',   dot: 'bg-gray-400'   },
  call_queued:      { label: 'Queued',        color: 'text-blue-600',   bg: 'bg-blue-50',    dot: 'bg-blue-400'   },
  call_initiated:   { label: 'Initiated',     color: 'text-indigo-600', bg: 'bg-indigo-50',  dot: 'bg-indigo-400' },
  call_ringing:     { label: 'Ringing',       color: 'text-violet-600', bg: 'bg-violet-50',  dot: 'bg-violet-400' },
  call_in_progress: { label: 'In Progress',   color: 'text-green-700',  bg: 'bg-green-50',   dot: 'bg-green-500'  },
  call_completed:   { label: 'Completed',     color: 'text-emerald-600',bg: 'bg-emerald-50', dot: 'bg-emerald-500'},
  call_busy:        { label: 'Busy',          color: 'text-orange-600', bg: 'bg-orange-50',  dot: 'bg-orange-400' },
  call_no_answer:   { label: 'No Answer',     color: 'text-amber-600',  bg: 'bg-amber-50',   dot: 'bg-amber-400'  },
  call_failed:      { label: 'Failed',        color: 'text-red-600',    bg: 'bg-red-50',     dot: 'bg-red-400'    },
  call_canceled:    { label: 'Canceled',      color: 'text-gray-500',   bg: 'bg-gray-100',   dot: 'bg-gray-400'   },
  interrupted:      { label: 'Interrupted',   color: 'text-rose-600',   bg: 'bg-rose-50',    dot: 'bg-rose-400'   },
};

// When the call is answered, show the agent's conversation phase instead of the raw call state.
const PHASE_BADGE_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  not_started:   { label: 'Connected',     color: 'text-green-700',  bg: 'bg-green-50',   dot: 'bg-green-500'   },
  collecting:    { label: 'Collecting',    color: 'text-blue-700',   bg: 'bg-blue-50',    dot: 'bg-blue-500'    },
  all_submitted: { label: 'All Submitted', color: 'text-purple-700', bg: 'bg-purple-50',  dot: 'bg-purple-500'  },
  complete:      { label: 'Complete',      color: 'text-emerald-700',bg: 'bg-emerald-50', dot: 'bg-emerald-500' },
};

// Session complete — all docs uploaded and verification passed
const VERIFIED_STATUS = {
  label: 'Verified',
  color: 'text-emerald-700',
  bg:    'bg-emerald-50',
  dot:   'bg-emerald-600',
};

// Rescheduled — call ended but session not complete, or call failed/busy/no-answer with retries remaining
const RESCHEDULED_STATUS = {
  label: 'Rescheduled',
  color: 'text-amber-700',
  bg:    'bg-amber-50',
  dot:   'bg-amber-500',
};

// Max Attempts — too many failed/unanswered calls; no more automatic retries
const MAX_ATTEMPTS_STATUS = {
  label: 'Max Attempts',
  color: 'text-red-700',
  bg:    'bg-red-50',
  dot:   'bg-red-500',
};

// Default max retries threshold (matches workflow default; ideally passed from session metadata)
const DEFAULT_MAX_CALL_ATTEMPTS = 3;

// Twilio call-failure statuses (the call never connected or was interrupted)
const CALL_FAILURE_STATUSES: AgentSessionStatus[] = [
  'call_busy', 'call_no_answer', 'call_failed', 'call_canceled', 'interrupted',
];

/**
 * Return a single unified status badge config for the session card header.
 *
 * Display rules:
 *   pending / queued / initiated / ringing
 *     → raw call-leg state
 *
 *   call_in_progress
 *     → agent conversation phase (Connected / Collecting / All Submitted / Complete)
 *
 *   call_completed + agent_phase === 'complete'
 *     → "Verified" — session fully done (all docs collected & verified)
 *
 *   call_completed + agent_phase !== 'complete'
 *     → "Rescheduled" — call ended but documents not yet collected; needs another call
 *
 *   call_busy / no-answer / failed / canceled / interrupted + attempts < max
 *     → "Rescheduled" — will be called again
 *
 *   call_busy / no-answer / failed / canceled / interrupted + attempts ≥ max
 *     → "Max Attempts" — no more automatic retries
 */
function getUnifiedStatus(session: AgentSession): { label: string; color: string; bg: string; dot: string } {
  switch (session.status as AgentSessionStatus) {
    // ── Pre-answer: show raw call leg state ─────────────────────────────────
    case 'pending':
    case 'call_queued':
    case 'call_initiated':
    case 'call_ringing':
      return STATUS_CONFIG[session.status as AgentSessionStatus];

    // ── Live call: show agent conversation phase ─────────────────────────────
    case 'call_in_progress':
      return PHASE_BADGE_CONFIG[session.agent_phase] ?? PHASE_BADGE_CONFIG.not_started;

    // ── Call ended ───────────────────────────────────────────────────────────
    case 'call_completed':
      // Session is truly done only when ALL documents have been collected & verified
      if (session.agent_phase === 'complete') return VERIFIED_STATUS;
      // Call ended but session still has pending documents — needs a follow-up call
      return RESCHEDULED_STATUS;

    // ── Call never connected / was interrupted ───────────────────────────────
    case 'call_busy':
    case 'call_no_answer':
    case 'call_failed':
    case 'call_canceled':
    case 'interrupted':
      if (session.attempt_count >= DEFAULT_MAX_CALL_ATTEMPTS) return MAX_ATTEMPTS_STATUS;
      return RESCHEDULED_STATUS;

    default:
      return STATUS_CONFIG.pending;
  }
}

/**
 * True when no more calls should/can be placed for this session.
 *   • Verified — all docs collected and verified
 *   • Max Attempts — too many failed calls
 */
function isSessionDone(session: AgentSession): boolean {
  if (session.status === 'call_completed' && session.agent_phase === 'complete') return true;
  if (CALL_FAILURE_STATUSES.includes(session.status) && session.attempt_count >= DEFAULT_MAX_CALL_ATTEMPTS) return true;
  return false;
}

/** True when the session is waiting to be called again (rescheduled). */
function isSessionRescheduled(session: AgentSession): boolean {
  if (session.status === 'call_completed' && session.agent_phase !== 'complete') return true;
  if (CALL_FAILURE_STATUSES.includes(session.status) && session.attempt_count < DEFAULT_MAX_CALL_ATTEMPTS) return true;
  return false;
}

const VERIFY_CONFIG = {
  requested: { label: 'Requested',  color: 'text-blue-600',   bg: 'bg-blue-50',   icon: '📤' },
  pending:   { label: 'Pending',    color: 'text-amber-600',  bg: 'bg-amber-50',  icon: '⏳' },
  passed:    { label: 'Passed',     color: 'text-emerald-600',bg: 'bg-emerald-50',icon: '✅' },
  failed:    { label: 'Failed',     color: 'text-red-600',    bg: 'bg-red-50',    icon: '❌' },
};

// ─── Active status set ────────────────────────────────────────────────────────
const ACTIVE_STATUSES: AgentSessionStatus[] = ['call_queued', 'call_initiated', 'call_ringing', 'call_in_progress'];
const TERMINAL_STATUSES: AgentSessionStatus[] = ['call_completed', 'call_failed', 'call_busy', 'call_no_answer', 'call_canceled', 'interrupted'];

// ─── Session Card ─────────────────────────────────────────────────────────────

function SessionCard({ session }: { session: AgentSession }) {
  const dispatch = useAppDispatch();
  const [expanded, setExpanded] = useState(false);
  const [mockVerifyOpen, setMockVerifyOpen] = useState<string | null>(null);
  const [mockReason, setMockReason] = useState('');
  const [downloadingDoc, setDownloadingDoc] = useState<string | null>(null);
  const actionLoading = useAppSelector((s) => s.sessions.actionLoading);

  const unifiedStatus = getUnifiedStatus(session);

  // Compute doc stats
  const docEntries = Object.entries(session.verification_results);
  const totalDocs = session.items_queue_length > 0
    ? Object.keys(session.verification_results).length || session.items_queue_length
    : 0;
  const passedDocs = docEntries.filter(([, v]) => v === 'passed').length;
  const docProgress = totalDocs > 0 ? (passedDocs / totalDocs) * 100 : 0;

  const isActive   = ACTIVE_STATUSES.includes(session.status);
  const isDone     = isSessionDone(session);        // verified ✓ or max-attempts
  const isVerified = session.status === 'call_completed' && session.agent_phase === 'complete';
  const isMaxAttempts = CALL_FAILURE_STATUSES.includes(session.status) && session.attempt_count >= DEFAULT_MAX_CALL_ATTEMPTS;
  const isRescheduled = isSessionRescheduled(session);

  const callLoading = actionLoading[session.session_id];
  const interruptLoading = actionLoading[`interrupt-${session.session_id}`];

  const handleRefresh = async () => {
    try {
      await dispatch(fetchAgentSession(session.session_id)).unwrap();
    } catch {
      toast.error('Failed to refresh session');
    }
  };

  const handleInitiateCall = async () => {
    try {
      const result = await dispatch(initiateCall(session.session_id)).unwrap();
      if (result.result?.status === 'skipped') {
        toast('Call skipped — Twilio not configured', { icon: '⚠️' });
      } else {
        toast.success(`Call initiated (${result.result?.call_sid?.slice(0, 12)}...)`);
      }
      setTimeout(() => handleRefresh(), 2000);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to initiate call');
    }
  };

  const handleInterrupt = async () => {
    if (!confirm('Force-close this session?')) return;
    try {
      await dispatch(interruptSession(session.session_id)).unwrap();
      toast.success('Session interrupted');
      setTimeout(() => handleRefresh(), 1000);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to interrupt session');
    }
  };

  const handleSimulateUpload = async (docKey: string) => {
    try {
      await dispatch(simulateDocUpload({ sessionId: session.session_id, documentKey: docKey })).unwrap();
      toast.success(`Upload simulated: ${docKey}`);
      setTimeout(() => handleRefresh(), 1500);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to simulate upload');
    }
  };

  const handleDownload = async (docKey: string) => {
    setDownloadingDoc(docKey);
    try {
      const { download_url } = await agentApi.getMediaDownloadUrl(session.session_id, docKey);
      window.open(download_url, '_blank', 'noopener,noreferrer');
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to get download URL');
    } finally {
      setDownloadingDoc(null);
    }
  };

  const handleMockVerify = async (docKey: string, passed: boolean) => {
    try {
      await dispatch(mockVerifyResult({
        sessionId: session.session_id,
        documentKey: docKey,
        passed,
        reason: mockReason || (passed ? 'Verification passed' : 'Verification failed'),
      })).unwrap();
      toast.success(`Mock ${passed ? 'pass' : 'fail'} sent for ${docKey}`);
      setMockVerifyOpen(null);
      setMockReason('');
      setTimeout(() => handleRefresh(), 1500);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to send mock result');
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return null;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatRelative = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return new Date(iso).toLocaleDateString('en-IN');
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card overflow-hidden"
    >
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Status icon — reflects the semantic session state */}
          <div className={clsx(
            'w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5',
            isActive      ? 'bg-green-50'   :
            isVerified    ? 'bg-emerald-50' :
            isMaxAttempts ? 'bg-red-50'     :
            isRescheduled ? 'bg-amber-50'   :
            'bg-blue-50'
          )}>
            {isActive ? (
              <PhoneCall className="w-4 h-4 text-green-600 animate-pulse" />
            ) : isVerified ? (
              <CheckCircle className="w-4 h-4 text-emerald-600" />
            ) : isMaxAttempts ? (
              <XCircle className="w-4 h-4 text-red-500" />
            ) : isRescheduled ? (
              <RefreshCw className="w-4 h-4 text-amber-600" />
            ) : (
              <Phone className="w-4 h-4 text-blue-500" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-900">
                {session.customer_phone}
              </span>
              {session.customer_name && (
                <span className="text-xs text-gray-500">({session.customer_name})</span>
              )}
              <span className={clsx('badge text-xs', unifiedStatus.bg, unifiedStatus.color)}>
                <span className={clsx('w-1.5 h-1.5 rounded-full', unifiedStatus.dot, isActive && 'animate-pulse')} />
                {unifiedStatus.label}
              </span>
            </div>

            <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500 flex-wrap">
              <span className="flex items-center gap-1">
                <Activity className="w-3 h-3" />
                {session.attempt_count} attempt{session.attempt_count !== 1 ? 's' : ''}
              </span>
              {session.items_queue_length > 0 && (
                <span className="flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  {session.current_item_index}/{session.items_queue_length} items
                </span>
              )}
              {session.pending_upload_doc && (
                <span className="flex items-center gap-1 text-amber-600">
                  <Upload className="w-3 h-3" />
                  Waiting: {session.pending_upload_doc}
                </span>
              )}
              <span className="flex items-center gap-1 ml-auto">
                <Timer className="w-3 h-3" />
                {formatRelative(session.created_at)}
              </span>
            </div>

            {/* Doc progress bar */}
            {totalDocs > 0 && (
              <div className="mt-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-500">Documents: {passedDocs}/{totalDocs} verified</span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${docProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <button
              onClick={handleRefresh}
              className="btn-ghost btn-sm p-1.5"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
            </button>
            {/* Show call button for pending + rescheduled sessions; hide once verified or max-attempts */}
            {!isActive && !isDone && (
              <button
                onClick={handleInitiateCall}
                disabled={!!callLoading}
                className="btn-primary btn-sm"
                title="Initiate / re-schedule call"
              >
                {callLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Phone className="w-3.5 h-3.5" />}
              </button>
            )}
            {isActive && (
              <button
                onClick={handleInterrupt}
                disabled={!!interruptLoading}
                className="btn-danger btn-sm"
                title="Interrupt session"
              >
                {interruptLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <StopCircle className="w-3.5 h-3.5" />}
              </button>
            )}
            <button
              onClick={() => setExpanded((e) => !e)}
              className="btn-secondary btn-sm"
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {expanded ? 'Less' : 'Details'}
            </button>
          </div>
        </div>
      </div>

      {/* Detail Panel */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-gray-100 bg-gray-50 p-4 space-y-4">

              {/* Session ID + workflow */}
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>Session: <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200 text-gray-700">{session.session_id.slice(0, 16)}...</code></span>
                <Link href={`/workflows/${session.workflow_id}`} className="text-brand-600 hover:underline">
                  View Workflow →
                </Link>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

                {/* Document Verification Status */}
                {Object.keys(session.verification_results).length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" /> Documents
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(session.verification_results).map(([docKey, status]) => {
                        const vCfg = VERIFY_CONFIG[status] ?? VERIFY_CONFIG.pending;
                        const uploadLoading = actionLoading[`upload-${session.session_id}-${docKey}`];
                        const verifyLoadingPass = actionLoading[`verify-${session.session_id}-${docKey}`];
                        const hasS3 = !!(session.documents_status as Record<string, any>)[docKey]?.s3_key;
                        const isDownloading = downloadingDoc === docKey;
                        return (
                          <div key={docKey} className={clsx('rounded-lg p-2 flex items-start gap-2', vCfg.bg)}>
                            <span className="text-sm flex-shrink-0">{vCfg.icon}</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-gray-800 truncate">{docKey}</p>
                              <div className="flex items-center gap-1.5">
                                <p className={clsx('text-xs', vCfg.color)}>{vCfg.label}</p>
                                {hasS3 && (
                                  <span className="text-xs text-emerald-600 flex items-center gap-0.5">
                                    · <Download className="w-2.5 h-2.5" /> S3
                                  </span>
                                )}
                              </div>
                            </div>
                            {/* S3 download button — shown whenever the file was uploaded to S3 */}
                            {hasS3 && (
                              <button
                                onClick={() => handleDownload(docKey)}
                                disabled={isDownloading}
                                className="btn-sm text-xs bg-white text-blue-600 border border-blue-200 hover:bg-blue-50 flex items-center gap-1"
                                title="Download from S3 (signed URL, valid 1h)"
                              >
                                {isDownloading
                                  ? <Loader2 className="w-3 h-3 animate-spin" />
                                  : <Download className="w-3 h-3" />}
                              </button>
                            )}
                            {/* Dev actions */}
                            {status === 'requested' && (
                              <button
                                onClick={() => handleSimulateUpload(docKey)}
                                disabled={!!uploadLoading}
                                className="btn-secondary btn-sm text-xs"
                                title="Simulate upload (dev)"
                              >
                                {uploadLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                              </button>
                            )}
                            {status === 'pending' && (
                              <div className="flex gap-1">
                                {mockVerifyOpen === docKey ? (
                                  <div className="flex flex-col gap-1">
                                    <input
                                      type="text"
                                      placeholder="Reason (optional)"
                                      value={mockReason}
                                      onChange={(e) => setMockReason(e.target.value)}
                                      className="text-xs border border-gray-200 rounded px-1.5 py-0.5 w-28 bg-white"
                                    />
                                    <div className="flex gap-1">
                                      <button
                                        onClick={() => handleMockVerify(docKey, true)}
                                        disabled={!!verifyLoadingPass}
                                        className="btn-sm text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                                      >
                                        {verifyLoadingPass ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                                        Pass
                                      </button>
                                      <button
                                        onClick={() => handleMockVerify(docKey, false)}
                                        className="btn-sm text-xs bg-red-50 text-red-600 border border-red-200 hover:bg-red-100"
                                      >
                                        <ShieldX className="w-3 h-3" /> Fail
                                      </button>
                                      <button
                                        onClick={() => setMockVerifyOpen(null)}
                                        className="btn-sm text-xs text-gray-500"
                                      >✕</button>
                                    </div>
                                  </div>
                                ) : (
                                  <button
                                    onClick={() => setMockVerifyOpen(docKey)}
                                    className="btn-secondary btn-sm text-xs"
                                    title="Mock verify result (dev)"
                                  >
                                    <Zap className="w-3 h-3" /> Mock
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}

                      {/* Pending upload doc not yet in verification_results */}
                      {session.pending_upload_doc && !session.verification_results[session.pending_upload_doc] && (
                        <div className="rounded-lg p-2 flex items-start gap-2 bg-amber-50">
                          <span className="text-sm">📤</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-800 truncate">{session.pending_upload_doc}</p>
                            <p className="text-xs text-amber-600">Awaiting upload</p>
                          </div>
                          <button
                            onClick={() => handleSimulateUpload(session.pending_upload_doc!)}
                            disabled={!!actionLoading[`upload-${session.session_id}-${session.pending_upload_doc}`]}
                            className="btn-secondary btn-sm text-xs"
                            title="Simulate upload (dev)"
                          >
                            <Upload className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Question Answers */}
                {Object.keys(session.question_answers).length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5" /> Answers
                    </h4>
                    <div className="space-y-1.5">
                      {Object.entries(session.question_answers).map(([qId, answer]) => (
                        <div key={qId} className="bg-white rounded-lg px-2.5 py-1.5 border border-gray-200">
                          <p className="text-xs text-gray-500 truncate">{qId.slice(0, 24)}...</p>
                          <p className="text-xs font-medium text-gray-800">{answer}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Call Attempts Timeline */}
                {session.call_attempts.length > 0 && (
                  <div className="sm:col-span-2">
                    <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5" /> Call Attempts
                    </h4>
                    <div className="space-y-1.5">
                      {session.call_attempts.map((attempt) => (
                        <div key={attempt.call_sid} className="bg-white rounded-lg px-3 py-2 border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-gray-700">
                                #{attempt.attempt_number}
                              </span>
                              <code className="text-xs text-gray-500">{attempt.call_sid.slice(0, 16)}...</code>
                              <span className={clsx(
                                'badge text-xs',
                                attempt.status === 'completed' ? 'bg-emerald-50 text-emerald-600' :
                                attempt.status === 'in-progress' ? 'bg-green-50 text-green-700' :
                                attempt.status === 'failed' ? 'bg-red-50 text-red-600' :
                                'bg-gray-100 text-gray-500'
                              )}>
                                {attempt.status ?? 'unknown'}
                              </span>
                              {attempt.duration_seconds && (
                                <span className="text-xs text-gray-400">
                                  {formatDuration(attempt.duration_seconds)}
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-gray-400">
                              {formatTime(attempt.initiated_at)}
                            </span>
                          </div>
                          {attempt.answered_at && (
                            <p className="text-xs text-gray-400 mt-0.5">
                              Answered: {formatTime(attempt.answered_at)}
                              {attempt.ended_at && ` → Ended: ${formatTime(attempt.ended_at)}`}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Failed docs re-queue */}
                {session.failed_docs_requeue.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-red-600 mb-2 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" /> Failed (Re-queued)
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {session.failed_docs_requeue.map((docKey) => (
                        <span key={docKey} className="badge bg-red-50 text-red-600 text-xs">
                          {docKey}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Timestamps */}
              <div className="pt-2 border-t border-gray-200 flex flex-wrap gap-4 text-xs text-gray-400">
                <span>Created: {formatTime(session.created_at)}</span>
                {session.session_started_at && (
                  <span>Started: {formatTime(session.session_started_at)}</span>
                )}
                {session.session_ended_at && (
                  <span>Ended: {formatTime(session.session_ended_at)}</span>
                )}
                <span className="ml-auto">Updated: {formatTime(session.updated_at)}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Filter Tab ───────────────────────────────────────────────────────────────

type FilterTab = 'all' | 'active' | 'verified' | 'rescheduled';

function filterSessions(sessions: AgentSession[], tab: FilterTab): AgentSession[] {
  switch (tab) {
    case 'active':
      // Currently on a call, or waiting to be called for the first time
      return sessions.filter((s) => ACTIVE_STATUSES.includes(s.status) || s.status === 'pending');

    case 'verified':
      // Session is fully complete — all documents collected & verified
      return sessions.filter((s) => s.agent_phase === 'complete');

    case 'rescheduled':
      // Needs another call (busy/no-answer/call ended early) OR hit max attempts
      return sessions.filter((s) => isSessionRescheduled(s) || isSessionDone(s) && s.agent_phase !== 'complete');

    default:
      return sessions;
  }
}

// ─── Sessions Page ────────────────────────────────────────────────────────────

export default function SessionsPage() {
  const dispatch = useAppDispatch();
  const { sessions, total, isLoading, error, lastFetchedAt } = useAppSelector((s) => s.sessions);

  const [autoRefresh, setAutoRefresh] = useState(false);
  const [filter, setFilter] = useState<FilterTab>('all');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(() => {
    dispatch(fetchAgentSessions());
  }, [dispatch]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, 5000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, load]);

  const filtered = filterSessions(sessions, filter);
  const activeCount      = sessions.filter((s) => ACTIVE_STATUSES.includes(s.status)).length;
  // "Verified" = session fully done (all docs collected & verified)
  const verifiedCount    = sessions.filter((s) => s.agent_phase === 'complete').length;
  // "Rescheduled" = needs another call OR hit max attempts
  const rescheduledCount = sessions.filter(
    (s) => isSessionRescheduled(s) || (isSessionDone(s) && s.agent_phase !== 'complete')
  ).length;

  const tabs: { id: FilterTab; label: string; count: number }[] = [
    { id: 'all',         label: 'All',         count: total           },
    { id: 'active',      label: 'Active',       count: activeCount     },
    { id: 'verified',    label: 'Verified',     count: verifiedCount   },
    { id: 'rescheduled', label: 'Rescheduled',  count: rescheduledCount},
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
              <PhoneCall className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Sessions</h1>
              <p className="text-sm text-gray-500">
                Monitor active and past AI agent verification sessions
                {lastFetchedAt && (
                  <span className="ml-2 text-gray-400">
                    · Updated {new Date(lastFetchedAt).toLocaleTimeString('en-IN')}
                  </span>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              disabled={isLoading}
              className="btn-secondary btn-sm"
            >
              <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} />
              Refresh
            </button>
            <button
              onClick={() => setAutoRefresh((v) => !v)}
              className={clsx(
                'btn-sm flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium border transition-colors',
                autoRefresh
                  ? 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              )}
            >
              <Activity className={clsx('w-4 h-4', autoRefresh && 'animate-pulse')} />
              {autoRefresh ? 'Auto: ON' : 'Auto: OFF'}
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Sessions', value: total,            icon: MessageSquare, color: 'text-gray-600',   bg: 'bg-gray-100'   },
          { label: 'Active',         value: activeCount,      icon: PhoneCall,     color: 'text-green-600',  bg: 'bg-green-50'   },
          { label: 'Verified',       value: verifiedCount,    icon: CheckCircle,   color: 'text-emerald-600',bg: 'bg-emerald-50' },
          { label: 'Rescheduled',    value: rescheduledCount, icon: RefreshCw,     color: 'text-amber-600',  bg: 'bg-amber-50'   },
        ].map((stat) => (
          <div key={stat.label} className="card p-4">
            <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center mb-2', stat.bg)}>
              <stat.icon className={clsx('w-4 h-4', stat.color)} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
            <p className="text-xs text-gray-500">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="card p-1.5 flex gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id)}
            className={clsx(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              filter === tab.id
                ? 'bg-brand-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            )}
          >
            {tab.label}
            <span className={clsx(
              'text-xs px-1.5 py-0.5 rounded-full',
              filter === tab.id ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
            )}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 rounded-xl border border-red-200">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={load} className="ml-auto btn-secondary btn-sm">Retry</button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && sessions.length === 0 && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-xl bg-gray-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-100 rounded w-1/3" />
                  <div className="h-3 bg-gray-100 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Session list */}
      {!isLoading && filtered.length === 0 && !error && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-16 text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center mx-auto mb-4">
            <PhoneCall className="w-8 h-8 text-green-300" />
          </div>
          <h2 className="text-base font-semibold text-gray-900 mb-2">
            {filter === 'all' ? 'No sessions yet' : `No ${filter} sessions`}
          </h2>
          <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
            {filter === 'all'
              ? 'Initiate a session from an active workflow to see it here.'
              : `No sessions match the "${filter}" filter.`}
          </p>
          {filter === 'all' && (
            <Link href="/workflows" className="btn-primary btn-sm mt-4 inline-flex items-center gap-2">
              <Play className="w-4 h-4" /> Go to Workflows
            </Link>
          )}
        </motion.div>
      )}

      <AnimatePresence>
        <div className="space-y-3">
          {filtered.map((session) => (
            <SessionCard key={session.session_id} session={session} />
          ))}
        </div>
      </AnimatePresence>
    </div>
  );
}
