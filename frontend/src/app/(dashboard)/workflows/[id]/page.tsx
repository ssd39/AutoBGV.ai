'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
  ArrowLeft, Edit, Play, Copy, Trash2, CheckCircle,
  FileText, HelpCircle, Clock, RefreshCw, MessageSquare,
  Settings, Loader2, AlertCircle, Phone, X, User,
  Mail, Hash, ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchWorkflow, activateWorkflow, duplicateWorkflow,
  deleteWorkflow, clearCurrentWorkflow,
} from '@/store/workflowSlice';
import { workflowApi } from '@/lib/api';
import { Session } from '@/types';
import { CATEGORY_CONFIG, STATUS_CONFIG, DOC_CATEGORY_CONFIG, QUESTION_TYPE_CONFIG } from '@/lib/constants';
import clsx from 'clsx';

// ─── Initiate Session Modal ───────────────────────────────────────────────────

interface InitiateSessionModalProps {
  workflowId: string;
  workflowName: string;
  onClose: () => void;
  onSuccess: (session: Session) => void;
}

function InitiateSessionModal({ workflowId, workflowName, onClose, onSuccess }: InitiateSessionModalProps) {
  const [form, setForm] = useState({
    customer_phone: '',
    customer_name: '',
    customer_email: '',
    external_reference_id: '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!form.customer_phone.trim()) {
      errs.customer_phone = 'Phone number is required';
    } else if (!/^\+?[1-9]\d{7,14}$/.test(form.customer_phone.replace(/\s/g, ''))) {
      errs.customer_phone = 'Enter a valid phone number (e.g. +919876543210)';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setIsSaving(true);
    try {
      const session = await workflowApi.createSession(workflowId, {
        customer_phone: form.customer_phone.trim(),
        customer_name: form.customer_name.trim() || undefined,
        customer_email: form.customer_email.trim() || undefined,
        external_reference_id: form.external_reference_id.trim() || undefined,
      });
      onSuccess(session);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to create session');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 12 }}
        className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden z-10"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-green-50 flex items-center justify-center">
              <Phone className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-900">Initiate Session</h2>
              <p className="text-xs text-gray-500">{workflowName}</p>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded-lg">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Phone */}
          <div>
            <label className="label">
              Customer Phone <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="tel"
                placeholder="+919876543210"
                value={form.customer_phone}
                onChange={(e) => setForm((f) => ({ ...f, customer_phone: e.target.value }))}
                className={clsx('input pl-9', errors.customer_phone && 'border-red-300 focus:ring-red-200')}
              />
            </div>
            {errors.customer_phone && (
              <p className="text-xs text-red-500 mt-1">{errors.customer_phone}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              The AI agent will call this number. Use E.164 format with country code.
            </p>
          </div>

          {/* Name */}
          <div>
            <label className="label">Customer Name <span className="text-gray-400 font-normal">(optional)</span></label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Rahul Sharma"
                value={form.customer_name}
                onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
                className="input pl-9"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="label">Customer Email <span className="text-gray-400 font-normal">(optional)</span></label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="email"
                placeholder="rahul@example.com"
                value={form.customer_email}
                onChange={(e) => setForm((f) => ({ ...f, customer_email: e.target.value }))}
                className="input pl-9"
              />
            </div>
          </div>

          {/* External Reference ID */}
          <div>
            <label className="label">
              Reference ID <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <div className="relative">
              <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="LOAN-2024-001"
                value={form.external_reference_id}
                onChange={(e) => setForm((f) => ({ ...f, external_reference_id: e.target.value }))}
                className="input pl-9"
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">Your internal loan ID, application number, etc.</p>
          </div>

          {/* Info */}
          <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-xl">
            <AlertCircle className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700 leading-relaxed">
              Once created, the AI agent will call the customer immediately.
              If Twilio is not configured, the session will be created but no call will be placed.
            </p>
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={isSaving} className="btn-primary">
              {isSaving ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Creating…</>
              ) : (
                <><Play className="w-4 h-4" /> Initiate Session</>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

// ─── Session Created Banner ───────────────────────────────────────────────────

function SessionCreatedBanner({ session, onDismiss }: { session: Session; onDismiss: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200"
    >
      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-green-800">Session created!</p>
        <p className="text-xs text-green-600 mt-0.5">
          ID: <code className="font-mono">{session.id.slice(0, 16)}…</code>
          {' '}· Phone: {session.customer_phone}
          {' '}· Status: {session.status}
        </p>
      </div>
      <Link href="/sessions" className="btn-sm bg-green-600 text-white hover:bg-green-700 flex items-center gap-1.5">
        <ExternalLink className="w-3.5 h-3.5" /> Monitor
      </Link>
      <button onClick={onDismiss} className="btn-ghost p-1.5">
        <X className="w-4 h-4 text-green-600" />
      </button>
    </motion.div>
  );
}

// ─── Workflow Detail Page ─────────────────────────────────────────────────────

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const id = params.id as string;

  const { currentWorkflow: wf, isLoadingWorkflow, workflowError } = useAppSelector((s) => s.workflows);
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [createdSession, setCreatedSession] = useState<Session | null>(null);

  useEffect(() => {
    dispatch(fetchWorkflow(id));
    return () => { dispatch(clearCurrentWorkflow()); };
  }, [dispatch, id]);

  const handleActivate = async () => {
    try {
      await dispatch(activateWorkflow(id)).unwrap();
      toast.success('Workflow activated!');
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to activate');
    }
  };

  const handleDuplicate = async () => {
    try {
      const result = await dispatch(duplicateWorkflow(id)).unwrap();
      toast.success('Workflow duplicated!');
      router.push(`/workflows/${result.id}`);
    } catch {
      toast.error('Failed to duplicate');
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${wf?.name}"? This cannot be undone.`)) return;
    try {
      await dispatch(deleteWorkflow(id)).unwrap();
      toast.success('Workflow deleted');
      router.push('/workflows');
    } catch {
      toast.error('Failed to delete workflow');
    }
  };

  const handleSessionCreated = (session: Session) => {
    setShowSessionModal(false);
    setCreatedSession(session);
    toast.success('Session initiated! AI agent will call the customer shortly.');
  };

  if (isLoadingWorkflow) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
      </div>
    );
  }

  if (workflowError || !wf) {
    return (
      <div className="card p-12 text-center max-w-lg mx-auto mt-12">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-gray-900 mb-2">Workflow not found</h2>
        <p className="text-sm text-gray-500 mb-4">{workflowError || 'This workflow does not exist.'}</p>
        <Link href="/workflows" className="btn-secondary">
          <ArrowLeft className="w-4 h-4" /> Back to Workflows
        </Link>
      </div>
    );
  }

  const category = CATEGORY_CONFIG[wf.category];
  const status = STATUS_CONFIG[wf.status];

  return (
    <>
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Breadcrumb & Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/workflows" className="btn-ghost btn-sm">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{category.icon}</span>
                <h1 className="text-xl font-bold text-gray-900">{wf.name}</h1>
              </div>
              {wf.description && (
                <p className="text-sm text-gray-500 mt-0.5 ml-8">{wf.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={clsx('badge', status.bg, status.color)}>
              <span className={clsx('w-1.5 h-1.5 rounded-full', status.dot)} />
              {status.label}
            </span>
            <Link href={`/workflows/${id}/edit`} className="btn-secondary btn-sm">
              <Edit className="w-4 h-4" /> Edit
            </Link>
            {wf.status === 'draft' && (
              <button onClick={handleActivate} className="btn-primary btn-sm">
                <CheckCircle className="w-4 h-4" /> Activate
              </button>
            )}
            {wf.status === 'active' && (
              <button
                onClick={() => setShowSessionModal(true)}
                className="btn-primary btn-sm"
              >
                <Play className="w-4 h-4" /> Initiate Session
              </button>
            )}
          </div>
        </div>

        {/* Session Created Banner */}
        <AnimatePresence>
          {createdSession && (
            <SessionCreatedBanner
              session={createdSession}
              onDismiss={() => setCreatedSession(null)}
            />
          )}
        </AnimatePresence>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Documents',   value: wf.documents.length,           icon: FileText,  color: 'text-blue-600',   bg: 'bg-blue-50'   },
            { label: 'Questions',   value: wf.questions.length,           icon: HelpCircle,color: 'text-purple-600', bg: 'bg-purple-50' },
            { label: 'Max Retries', value: wf.max_retry_attempts,         icon: RefreshCw, color: 'text-orange-600', bg: 'bg-orange-50' },
            { label: 'Timeout',     value: `${wf.session_timeout_minutes}m`, icon: Clock,  color: 'text-teal-600',   bg: 'bg-teal-50'   },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-4"
            >
              <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center mb-2', stat.bg)}>
                <stat.icon className={clsx('w-4 h-4', stat.color)} />
              </div>
              <p className="text-xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-500">{stat.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Draft warning */}
        {wf.status === 'draft' && (
          <div className="flex items-center gap-3 p-4 bg-amber-50 rounded-xl border border-amber-200">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-800">Draft Workflow</p>
              <p className="text-xs text-amber-600 mt-0.5">
                This workflow is in draft mode. Activate it to start initiating sessions.
              </p>
            </div>
            <button onClick={handleActivate} className="btn-primary btn-sm flex-shrink-0">
              <CheckCircle className="w-3.5 h-3.5" /> Activate Now
            </button>
          </div>
        )}

        {/* Active: quick session initiation tip */}
        {wf.status === 'active' && !createdSession && (
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200">
            <Play className="w-5 h-5 text-green-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-green-800">Workflow Active</p>
              <p className="text-xs text-green-600 mt-0.5">
                Ready to accept sessions. Click &ldquo;Initiate Session&rdquo; to start a customer verification call.
              </p>
            </div>
            <button
              onClick={() => setShowSessionModal(true)}
              className="btn-sm bg-green-600 text-white hover:bg-green-700 flex items-center gap-1.5 flex-shrink-0"
            >
              <Phone className="w-3.5 h-3.5" /> Initiate Now
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Documents */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-gray-500" />
                <h3 className="text-sm font-semibold text-gray-900">
                  Documents ({wf.documents.length})
                </h3>
              </div>
              <Link href={`/workflows/${id}/edit`} className="text-xs text-brand-600 hover:text-brand-700">
                Edit
              </Link>
            </div>
            {wf.documents.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">No documents configured</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {wf.documents.map((doc) => {
                  const catConfig = DOC_CATEGORY_CONFIG[doc.document_category];
                  return (
                    <div key={doc.id} className="flex items-center gap-3 px-4 py-3">
                      <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', catConfig?.bg)}>
                        <FileText className={clsx('w-3.5 h-3.5', catConfig?.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{doc.display_name}</p>
                        {doc.criteria_text && (
                          <p className="text-xs text-gray-400 truncate">{doc.criteria_text}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className={clsx('badge text-xs', catConfig?.bg, catConfig?.color)}>
                          {catConfig?.label}
                        </span>
                        {doc.is_required ? (
                          <span className="badge bg-red-50 text-red-600 text-xs">Req</span>
                        ) : (
                          <span className="badge bg-gray-50 text-gray-500 text-xs">Opt</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Questions */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-gray-500" />
                <h3 className="text-sm font-semibold text-gray-900">
                  Questions ({wf.questions.length})
                </h3>
              </div>
              <Link href={`/workflows/${id}/edit`} className="text-xs text-brand-600 hover:text-brand-700">
                Edit
              </Link>
            </div>
            {wf.questions.length === 0 ? (
              <div className="p-8 text-center text-sm text-gray-400">No questions configured</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {wf.questions.map((q) => {
                  const typeConfig = QUESTION_TYPE_CONFIG[q.question_type];
                  return (
                    <div key={q.id} className="flex items-start gap-3 px-4 py-3">
                      <span className="text-base flex-shrink-0 mt-0.5">{typeConfig?.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 leading-snug">{q.question_text}</p>
                        {q.question_type === 'multiple_choice' && q.options && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {q.options.slice(0, 2).join(' / ')}
                            {q.options.length > 2 && ` +${q.options.length - 2}`}
                          </p>
                        )}
                      </div>
                      <span className="badge bg-gray-100 text-gray-600 text-xs flex-shrink-0">
                        {typeConfig?.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        {(wf.welcome_message || wf.completion_message) && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <MessageSquare className="w-4 h-4 text-gray-500" />
              <h3 className="text-sm font-semibold text-gray-900">Agent Messages</h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {wf.welcome_message && (
                <div className="bg-brand-50 rounded-xl p-3">
                  <p className="text-xs font-medium text-brand-700 mb-1.5">👋 Welcome Message</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{wf.welcome_message}</p>
                </div>
              )}
              {wf.completion_message && (
                <div className="bg-green-50 rounded-xl p-3">
                  <p className="text-xs font-medium text-green-700 mb-1.5">✅ Completion Message</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{wf.completion_message}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Danger Zone */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Settings className="w-4 h-4 text-gray-500" /> Actions
          </h3>
          <div className="flex items-center gap-3 flex-wrap">
            <button onClick={handleDuplicate} className="btn-secondary btn-sm">
              <Copy className="w-4 h-4" /> Duplicate
            </button>
            <button onClick={handleDelete} className="btn-danger btn-sm">
              <Trash2 className="w-4 h-4" /> Delete Workflow
            </button>
          </div>
        </div>
      </div>

      {/* Session Modal */}
      <AnimatePresence>
        {showSessionModal && (
          <InitiateSessionModal
            workflowId={id}
            workflowName={wf.name}
            onClose={() => setShowSessionModal(false)}
            onSuccess={handleSessionCreated}
          />
        )}
      </AnimatePresence>
    </>
  );
}
