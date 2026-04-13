'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, Search, Trash2, ChevronDown, ChevronUp,
  GripVertical, FileText, Info, AlertCircle,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  addBuilderDocument, updateBuilderDocument, removeBuilderDocument,
} from '@/store/workflowSlice';
import {
  DOC_CATEGORY_CONFIG, DOCUMENT_CATEGORY_ORDER,
  DEFAULT_ALLOWED_FORMATS, DEFAULT_MAX_FILE_SIZE_MB,
} from '@/lib/constants';
import { DocumentCategory, DocumentTypeInfo, BuilderDocument } from '@/types';
import clsx from 'clsx';

export function Step2Documents() {
  const dispatch = useAppDispatch();
  const { builder, documentCatalog } = useAppSelector((s) => ({
    builder: s.workflows.builder,
    documentCatalog: s.workflows.documentCatalog,
  }));

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory | ''>('');
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);

  // Filter documents from catalog
  const filteredDocs = Object.entries(documentCatalog).flatMap(([cat, docs]) => {
    if (selectedCategory && cat !== selectedCategory) return [];
    return docs.filter((doc) =>
      !searchQuery ||
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Group by category for display
  const grouped: Record<string, DocumentTypeInfo[]> = {};
  filteredDocs.forEach((doc) => {
    if (!grouped[doc.category]) grouped[doc.category] = [];
    grouped[doc.category].push(doc as DocumentTypeInfo);
  });

  const addDocument = (doc: DocumentTypeInfo) => {
    // Check not already added
    if (builder.documents.find((d) => d.document_type_key === doc.key)) {
      return; // already added
    }
    dispatch(addBuilderDocument({
      document_type_key: doc.key,
      display_name: doc.name,
      document_category: doc.category as DocumentCategory,
      description: doc.description,
      is_required: true,
      order_index: builder.documents.length,
      criteria_text: '',
      allowed_formats: [...DEFAULT_ALLOWED_FORMATS],
      max_file_size_mb: DEFAULT_MAX_FILE_SIZE_MB,
    }));
  };

  const isAdded = (key: string) => builder.documents.some((d) => d.document_type_key === key);

  const orderedCategories = DOCUMENT_CATEGORY_ORDER.filter(
    (cat) => grouped[cat] && grouped[cat].length > 0
  );

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Document Requirements</h2>
        <p className="text-sm text-gray-500">
          Select the documents your customers need to upload for verification.
          You can set criteria for each document in natural language.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Document Catalog */}
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <p className="text-sm font-semibold text-gray-900 mb-3">Document Library</p>

            {/* Search */}
            <div className="flex items-center gap-2 border border-gray-200 rounded-lg px-3 py-2 mb-3">
              <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-sm outline-none flex-1 text-gray-700 placeholder-gray-400"
              />
            </div>

            {/* Category tabs */}
            <div className="flex gap-1 flex-wrap">
              <button
                onClick={() => setSelectedCategory('')}
                className={clsx(
                  'px-2.5 py-1 rounded-full text-xs font-medium transition-all',
                  selectedCategory === '' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                All
              </button>
              {DOCUMENT_CATEGORY_ORDER.map((cat) => {
                if (!documentCatalog[cat]?.length) return null;
                const config = DOC_CATEGORY_CONFIG[cat];
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat === selectedCategory ? '' : cat)}
                    className={clsx(
                      'px-2.5 py-1 rounded-full text-xs font-medium transition-all',
                      selectedCategory === cat ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {config.icon} {config.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Document list */}
          <div className="overflow-y-auto max-h-[420px] p-2 space-y-3">
            {Object.keys(grouped).length === 0 && (
              <div className="text-center py-8 text-sm text-gray-400">
                No documents found
              </div>
            )}
            {orderedCategories.map((cat) => (
              <div key={cat}>
                <div className="flex items-center gap-2 px-2 py-1 mb-1">
                  <span className="text-sm">{DOC_CATEGORY_CONFIG[cat]?.icon}</span>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    {DOC_CATEGORY_CONFIG[cat]?.label}
                  </span>
                </div>
                {grouped[cat].map((doc) => {
                  const added = isAdded(doc.key);
                  return (
                    <button
                      key={doc.key}
                      onClick={() => !added && addDocument(doc)}
                      disabled={added}
                      className={clsx(
                        'w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-all',
                        added
                          ? 'bg-green-50 border border-green-200 cursor-default'
                          : 'hover:bg-gray-50 border border-transparent hover:border-gray-200 cursor-pointer'
                      )}
                    >
                      <div className={clsx(
                        'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0',
                        added ? 'bg-green-100' : DOC_CATEGORY_CONFIG[doc.category as DocumentCategory]?.bg || 'bg-gray-100'
                      )}>
                        <FileText className={clsx(
                          'w-3.5 h-3.5',
                          added ? 'text-green-600' : DOC_CATEGORY_CONFIG[doc.category as DocumentCategory]?.color || 'text-gray-600'
                        )} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-gray-900 truncate">{doc.name}</p>
                        <p className="text-xs text-gray-400 truncate">{doc.issuing_authority}</p>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {doc.is_ovi && (
                          <span className="badge bg-blue-50 text-blue-700 text-xs">OVI</span>
                        )}
                        {added ? (
                          <span className="text-xs text-green-600 font-medium">Added</span>
                        ) : (
                          <Plus className="w-3.5 h-3.5 text-gray-400" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Added documents */}
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-900">Workflow Documents</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {builder.documents.length} document{builder.documents.length !== 1 ? 's' : ''} added
              </p>
            </div>
            {builder.documents.length === 0 && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 px-2.5 py-1.5 rounded-lg">
                <AlertCircle className="w-3.5 h-3.5" />
                Add at least one
              </div>
            )}
          </div>

          <div className="overflow-y-auto max-h-[420px] p-3 space-y-2">
            {builder.documents.length === 0 ? (
              <div className="text-center py-12 text-sm text-gray-400 flex flex-col items-center gap-2">
                <FileText className="w-8 h-8 text-gray-200" />
                <p>No documents added yet</p>
                <p className="text-xs">Select documents from the library on the left</p>
              </div>
            ) : (
              <AnimatePresence>
                {builder.documents.map((doc) => (
                  <DocumentItem
                    key={doc._id}
                    doc={doc}
                    isExpanded={expandedDocId === doc._id}
                    onToggle={() => setExpandedDocId(expandedDocId === doc._id ? null : doc._id)}
                    onRemove={() => dispatch(removeBuilderDocument(doc._id))}
                    onUpdate={(changes) => dispatch(updateBuilderDocument({ _id: doc._id, changes }))}
                  />
                ))}
              </AnimatePresence>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Document Item ────────────────────────────────────────────────────────────

interface DocumentItemProps {
  doc: BuilderDocument;
  isExpanded: boolean;
  onToggle: () => void;
  onRemove: () => void;
  onUpdate: (changes: Partial<BuilderDocument>) => void;
}

function DocumentItem({ doc, isExpanded, onToggle, onRemove, onUpdate }: DocumentItemProps) {
  const catConfig = DOC_CATEGORY_CONFIG[doc.document_category];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="border border-gray-200 rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-3 bg-white">
        <GripVertical className="w-4 h-4 text-gray-300 flex-shrink-0 cursor-grab" />

        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', catConfig?.bg || 'bg-gray-100')}>
          <FileText className={clsx('w-3.5 h-3.5', catConfig?.color || 'text-gray-600')} />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-gray-900 truncate">{doc.display_name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={clsx('text-xs', catConfig?.color || 'text-gray-500')}>
              {catConfig?.label}
            </span>
            {doc.is_required && (
              <span className="text-xs text-red-500">Required</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {doc.criteria_text && (
            <div className="w-2 h-2 rounded-full bg-brand-500" title="Has criteria" />
          )}
          <button
            onClick={onToggle}
            className="w-6 h-6 flex items-center justify-center rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all"
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onRemove}
            className="w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Expanded settings */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-3 pt-0 bg-gray-50/50 border-t border-gray-100 space-y-3">
              {/* Display Name */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Display Name</label>
                <input
                  type="text"
                  className="input text-xs py-1.5"
                  value={doc.display_name}
                  onChange={(e) => onUpdate({ display_name: e.target.value })}
                />
              </div>

              {/* Required toggle */}
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-gray-600">Required Document</label>
                <button
                  onClick={() => onUpdate({ is_required: !doc.is_required })}
                  className={clsx(
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                    doc.is_required ? 'bg-brand-600' : 'bg-gray-300'
                  )}
                >
                  <span className={clsx(
                    'inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform',
                    doc.is_required ? 'translate-x-4' : 'translate-x-1'
                  )} />
                </button>
              </div>

              {/* Criteria */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block flex items-center gap-1">
                  Verification Criteria
                  <span title="Describe in natural language what conditions the document must meet">
                    <Info className="w-3 h-3 text-gray-400" />
                  </span>
                </label>
                <textarea
                  className="textarea text-xs py-1.5"
                  rows={3}
                  placeholder="e.g., Must not be expired. Name must match applicant name. Both sides required. Not a photocopy."
                  value={doc.criteria_text || ''}
                  onChange={(e) => onUpdate({ criteria_text: e.target.value })}
                />
                <p className="text-xs text-gray-400 mt-1">
                  💡 Write in plain English — our AI will convert this to verification rules
                </p>
              </div>

              {/* Instructions */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">
                  Customer Instructions (shown via WhatsApp)
                </label>
                <textarea
                  className="textarea text-xs py-1.5"
                  rows={2}
                  placeholder="e.g., Upload front and back of your Aadhaar card as a single PDF or two separate images."
                  value={doc.instructions || ''}
                  onChange={(e) => onUpdate({ instructions: e.target.value })}
                />
              </div>

              {/* Max file size */}
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Max File Size</label>
                  <select
                    className="select text-xs py-1.5"
                    value={doc.max_file_size_mb}
                    onChange={(e) => onUpdate({ max_file_size_mb: Number(e.target.value) })}
                  >
                    {[2, 5, 10, 20, 50].map((n) => (
                      <option key={n} value={n}>{n} MB</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Allowed Formats</label>
                  <p className="text-xs text-gray-500 py-1.5">
                    {doc.allowed_formats.join(', ').toUpperCase()}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
