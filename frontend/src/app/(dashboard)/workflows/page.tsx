'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Plus, Search, Filter, GitBranch, MoreVertical,
  Zap, Copy, Trash2, Play, Eye, Edit, CheckCircle,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchWorkflows, deleteWorkflow, activateWorkflow,
  duplicateWorkflow,
} from '@/store/workflowSlice';
import { CATEGORY_CONFIG, STATUS_CONFIG } from '@/lib/constants';
import { WorkflowCategory, WorkflowStatus, WorkflowSummary } from '@/types';
import clsx from 'clsx';

export default function WorkflowsPage() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { workflows, totalWorkflows, isLoadingList, listError } = useAppSelector((s) => s.workflows);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<WorkflowCategory | ''>('');
  const [selectedStatus, setSelectedStatus] = useState<WorkflowStatus | ''>('');
  const [page, setPage] = useState(1);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const pageSize = 12;

  useEffect(() => {
    dispatch(fetchWorkflows({
      page,
      search: search || undefined,
      category: selectedCategory as WorkflowCategory || undefined,
      status: selectedStatus || undefined,
    }));
  }, [dispatch, page, search, selectedCategory, selectedStatus]);

  const totalPages = Math.ceil(totalWorkflows / pageSize);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete workflow "${name}"? This cannot be undone.`)) return;
    try {
      await dispatch(deleteWorkflow(id)).unwrap();
      toast.success('Workflow deleted');
    } catch {
      toast.error('Failed to delete workflow');
    }
  };

  const handleActivate = async (id: string) => {
    try {
      await dispatch(activateWorkflow(id)).unwrap();
      toast.success('Workflow activated!');
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to activate');
    }
  };

  const handleDuplicate = async (id: string) => {
    try {
      await dispatch(duplicateWorkflow(id)).unwrap();
      toast.success('Workflow duplicated');
      dispatch(fetchWorkflows({ page }));
    } catch {
      toast.error('Failed to duplicate');
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex items-center gap-3 flex-1 w-full">
          {/* Search */}
          <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 flex-1 max-w-sm">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search workflows..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="bg-transparent text-sm outline-none flex-1 text-gray-700 placeholder-gray-400"
            />
          </div>

          {/* Category filter */}
          <select
            value={selectedCategory}
            onChange={(e) => { setSelectedCategory(e.target.value as WorkflowCategory | ''); setPage(1); }}
            className="input text-sm w-auto py-2"
          >
            <option value="">All Categories</option>
            {Object.entries(CATEGORY_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.icon} {v.label}</option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={selectedStatus}
            onChange={(e) => { setSelectedStatus(e.target.value as WorkflowStatus | ''); setPage(1); }}
            className="input text-sm w-auto py-2 hidden sm:block"
          >
            <option value="">All Status</option>
            {Object.entries(STATUS_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </div>

        <Link href="/workflows/create" className="btn-primary flex-shrink-0">
          <Plus className="w-4 h-4" />
          New Workflow
        </Link>
      </div>

      {/* Loading */}
      {isLoadingList && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-gray-100 rounded w-3/4 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-4" />
              <div className="flex gap-2">
                <div className="h-6 bg-gray-100 rounded w-16" />
                <div className="h-6 bg-gray-100 rounded w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {listError && (
        <div className="card p-6 text-center text-red-600">
          <p className="text-sm">{listError}</p>
          <button className="btn-secondary btn-sm mt-2" onClick={() => dispatch(fetchWorkflows({}))}>
            Retry
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isLoadingList && !listError && workflows.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-12 text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
            <GitBranch className="w-8 h-8 text-brand-400" />
          </div>
          <h3 className="text-base font-semibold text-gray-900 mb-2">No workflows yet</h3>
          <p className="text-sm text-gray-500 mb-5 max-w-sm mx-auto">
            Create your first verification workflow from scratch or use a ready-made template.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link href="/workflows/create" className="btn-primary">
              <Plus className="w-4 h-4" /> Create Workflow
            </Link>
            <Link href="/workflows/create?tab=templates" className="btn-secondary">
              <Zap className="w-4 h-4" /> Use Template
            </Link>
          </div>
        </motion.div>
      )}

      {/* Workflow Grid */}
      {!isLoadingList && workflows.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          <AnimatePresence>
            {workflows.map((wf, i) => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                index={i}
                activeMenu={activeMenu}
                onMenuToggle={setActiveMenu}
                onActivate={handleActivate}
                onDuplicate={handleDuplicate}
                onDelete={handleDelete}
              />
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-gray-500">
            Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalWorkflows)} of {totalWorkflows}
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="btn-secondary btn-sm disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-gray-600 px-2">
              {page} / {totalPages}
            </span>
            <button
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="btn-secondary btn-sm disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Workflow Card Component ──────────────────────────────────────────────────

interface WorkflowCardProps {
  workflow: WorkflowSummary;
  index: number;
  activeMenu: string | null;
  onMenuToggle: (id: string | null) => void;
  onActivate: (id: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string, name: string) => void;
}

function WorkflowCard({
  workflow: wf, index, activeMenu, onMenuToggle,
  onActivate, onDuplicate, onDelete,
}: WorkflowCardProps) {
  const router = useRouter();
  const category = CATEGORY_CONFIG[wf.category];
  const status = STATUS_CONFIG[wf.status];
  const isMenuOpen = activeMenu === wf.id;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ delay: index * 0.04 }}
      className="card p-5 hover:shadow-card-hover hover:border-gray-300 transition-all duration-200 group"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xl">{category.icon}</span>
          <div className="min-w-0">
            <h3
              className="font-semibold text-gray-900 text-sm truncate cursor-pointer hover:text-brand-600"
              onClick={() => router.push(`/workflows/${wf.id}`)}
            >
              {wf.name}
            </h3>
            <span className={clsx('text-xs', category.color)}>{category.label}</span>
          </div>
        </div>

        {/* Menu */}
        <div className="relative flex-shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onMenuToggle(isMenuOpen ? null : wf.id); }}
            className="w-7 h-7 flex items-center justify-center rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          <AnimatePresence>
            {isMenuOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: -4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -4 }}
                transition={{ duration: 0.1 }}
                className="absolute right-0 top-8 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-10 w-44"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => { router.push(`/workflows/${wf.id}`); onMenuToggle(null); }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Eye className="w-4 h-4" /> View
                </button>
                <button
                  onClick={() => { router.push(`/workflows/${wf.id}/edit`); onMenuToggle(null); }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Edit className="w-4 h-4" /> Edit
                </button>
                {wf.status === 'draft' && (
                  <button
                    onClick={() => { onActivate(wf.id); onMenuToggle(null); }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-green-700 hover:bg-green-50"
                  >
                    <CheckCircle className="w-4 h-4" /> Activate
                  </button>
                )}
                <button
                  onClick={() => { onDuplicate(wf.id); onMenuToggle(null); }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Copy className="w-4 h-4" /> Duplicate
                </button>
                <div className="border-t border-gray-100 my-1" />
                <button
                  onClick={() => { onDelete(wf.id, wf.name); onMenuToggle(null); }}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Description */}
      {wf.description && (
        <p className="text-xs text-gray-500 mb-3 line-clamp-2 leading-relaxed">{wf.description}</p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 mb-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="font-medium text-gray-700">{wf.document_count}</span> docs
        </span>
        <span className="text-gray-300">·</span>
        <span className="flex items-center gap-1">
          <span className="font-medium text-gray-700">{wf.question_count}</span> questions
        </span>
        <span className="text-gray-300">·</span>
        <span className="flex items-center gap-1">
          <span className="font-medium text-gray-700">{wf.session_count}</span> sessions
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className={clsx('badge', status.bg, status.color)}>
          <span className={clsx('w-1.5 h-1.5 rounded-full', status.dot)} />
          {status.label}
        </span>

        {wf.status === 'active' ? (
          <Link
            href={`/workflows/${wf.id}`}
            className="text-xs font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            Initiate Session <Play className="w-3 h-3" />
          </Link>
        ) : (
          <Link
            href={`/workflows/${wf.id}/edit`}
            className="text-xs font-medium text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            Edit <Edit className="w-3 h-3" />
          </Link>
        )}
      </div>
    </motion.div>
  );
}
