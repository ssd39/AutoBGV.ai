'use client';

import { useAppSelector } from '@/store';
import { CATEGORY_CONFIG, DOC_CATEGORY_CONFIG, QUESTION_TYPE_CONFIG, STATUS_CONFIG } from '@/lib/constants';
import { CheckCircle, FileText, HelpCircle, Settings, MessageSquare } from 'lucide-react';
import clsx from 'clsx';

export function Step4Review() {
  const builder = useAppSelector((s) => s.workflows.builder);
  const category = CATEGORY_CONFIG[builder.category];

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Review Your Workflow</h2>
        <p className="text-sm text-gray-500">
          Review everything before saving. You can always edit after creation.
        </p>
      </div>

      {/* Summary card */}
      <div className="card p-5 bg-gradient-to-br from-brand-50 to-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-white border border-brand-200 flex items-center justify-center text-2xl flex-shrink-0 shadow-sm">
            {category.icon}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">{builder.name || 'Untitled Workflow'}</h3>
            {builder.description && (
              <p className="text-sm text-gray-500 mt-1">{builder.description}</p>
            )}
            <div className="flex items-center gap-3 mt-2">
              <span className={clsx('badge', category.bg, category.color)}>
                {category.icon} {category.label}
              </span>
              <span className="badge bg-gray-100 text-gray-600">
                {builder.documents.length} documents
              </span>
              <span className="badge bg-gray-100 text-gray-600">
                {builder.questions.length} questions
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Documents */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500" />
          <p className="text-sm font-semibold text-gray-900">
            Documents ({builder.documents.length})
          </p>
        </div>
        {builder.documents.length === 0 ? (
          <div className="p-6 text-center text-sm text-gray-400">No documents added</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {builder.documents.map((doc, i) => {
              const catConfig = DOC_CATEGORY_CONFIG[doc.document_category];
              return (
                <div key={doc._id} className="flex items-center gap-3 px-4 py-3">
                  <span className="text-xs text-gray-400 w-5 flex-shrink-0">{i + 1}</span>
                  <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', catConfig?.bg)}>
                    <FileText className={clsx('w-3.5 h-3.5', catConfig?.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{doc.display_name}</p>
                    {doc.criteria_text && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">
                        Criteria: {doc.criteria_text}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={clsx('badge text-xs', catConfig?.bg, catConfig?.color)}>
                      {catConfig?.label}
                    </span>
                    {doc.is_required ? (
                      <span className="badge bg-red-50 text-red-600 text-xs">Required</span>
                    ) : (
                      <span className="badge bg-gray-50 text-gray-500 text-xs">Optional</span>
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
        <div className="p-4 border-b border-gray-100 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-gray-500" />
          <p className="text-sm font-semibold text-gray-900">
            Questions ({builder.questions.length})
          </p>
        </div>
        {builder.questions.length === 0 ? (
          <div className="p-6 text-center text-sm text-gray-400">No questions added</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {builder.questions.map((q, i) => {
              const typeConfig = QUESTION_TYPE_CONFIG[q.question_type];
              return (
                <div key={q._id} className="flex items-start gap-3 px-4 py-3">
                  <span className="text-xs text-gray-400 w-5 flex-shrink-0 mt-0.5">{i + 1}</span>
                  <span className="text-base flex-shrink-0">{typeConfig?.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{q.question_text}</p>
                    {q.question_type === 'multiple_choice' && q.options && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Options: {q.options.slice(0, 3).join(', ')}
                        {q.options.length > 3 && ` +${q.options.length - 3} more`}
                      </p>
                    )}
                  </div>
                  <div className="flex-shrink-0">
                    <span className="badge bg-gray-100 text-gray-600 text-xs">
                      {typeConfig?.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Settings className="w-4 h-4 text-gray-500" />
          <p className="text-sm font-semibold text-gray-900">Settings</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-lg font-bold text-gray-900">{builder.max_retry_attempts}</p>
            <p className="text-xs text-gray-500">Max Retries</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-lg font-bold text-gray-900">
              {builder.session_timeout_minutes >= 60
                ? `${builder.session_timeout_minutes / 60}h`
                : `${builder.session_timeout_minutes}m`}
            </p>
            <p className="text-xs text-gray-500">Timeout</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-lg font-bold text-gray-900">
              {builder.welcome_message ? '✅' : '—'}
            </p>
            <p className="text-xs text-gray-500">Welcome Msg</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <p className="text-lg font-bold text-gray-900">Draft</p>
            <p className="text-xs text-gray-500">Initial Status</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      {(builder.welcome_message || builder.completion_message) && (
        <div className="card p-4 space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-4 h-4 text-gray-500" />
            <p className="text-sm font-semibold text-gray-900">Agent Messages</p>
          </div>
          {builder.welcome_message && (
            <div className="bg-brand-50 rounded-xl p-3">
              <p className="text-xs font-medium text-brand-700 mb-1">Welcome Message</p>
              <p className="text-sm text-gray-700">{builder.welcome_message}</p>
            </div>
          )}
          {builder.completion_message && (
            <div className="bg-green-50 rounded-xl p-3">
              <p className="text-xs font-medium text-green-700 mb-1">Completion Message</p>
              <p className="text-sm text-gray-700">{builder.completion_message}</p>
            </div>
          )}
        </div>
      )}

      {/* Ready to save */}
      <div className="flex items-center gap-3 p-4 bg-green-50 rounded-xl border border-green-200">
        <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-green-800">Ready to save</p>
          <p className="text-xs text-green-600 mt-0.5">
            Your workflow will be saved as a <strong>Draft</strong>. You can activate it once you&apos;re ready to start collecting documents.
          </p>
        </div>
      </div>
    </div>
  );
}
