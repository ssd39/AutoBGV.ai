'use client';

import { useAppDispatch, useAppSelector } from '@/store';
import { setBuilderField } from '@/store/workflowSlice';
import { CATEGORY_CONFIG } from '@/lib/constants';
import { WorkflowCategory } from '@/types';
import clsx from 'clsx';

export function Step1BasicInfo() {
  const dispatch = useAppDispatch();
  const builder = useAppSelector((s) => s.workflows.builder);

  const set = (field: string, value: unknown) =>
    dispatch(setBuilderField({ field: field as keyof typeof builder, value }));

  return (
    <div className="card p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Workflow Details</h2>
        <p className="text-sm text-gray-500">
          Give your workflow a name and choose the type of verification it handles.
        </p>
      </div>

      {/* Name */}
      <div>
        <label className="label">
          Workflow Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          className="input"
          placeholder="e.g., Home Loan KYC, Insurance Claim Verification"
          value={builder.name}
          onChange={(e) => set('name', e.target.value)}
          maxLength={200}
        />
        <p className="text-xs text-gray-400 mt-1">{builder.name.length}/200</p>
      </div>

      {/* Description */}
      <div>
        <label className="label">Description</label>
        <textarea
          className="textarea"
          rows={3}
          placeholder="Describe what this workflow is for and who it applies to..."
          value={builder.description}
          onChange={(e) => set('description', e.target.value)}
          maxLength={2000}
        />
        <p className="text-xs text-gray-400 mt-1">{builder.description.length}/2000</p>
      </div>

      {/* Category */}
      <div>
        <label className="label">
          Category <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {(Object.entries(CATEGORY_CONFIG) as [WorkflowCategory, typeof CATEGORY_CONFIG[WorkflowCategory]][]).map(
            ([key, config]) => (
              <button
                key={key}
                type="button"
                onClick={() => set('category', key)}
                className={clsx(
                  'flex flex-col items-center gap-2 p-3 rounded-xl border-2 text-center transition-all duration-150',
                  builder.category === key
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                )}
              >
                <span className="text-2xl">{config.icon}</span>
                <span className={clsx(
                  'text-xs font-medium',
                  builder.category === key ? 'text-brand-700' : 'text-gray-700'
                )}>
                  {config.label}
                </span>
              </button>
            )
          )}
        </div>
      </div>

      {/* Advanced Settings */}
      <details className="group">
        <summary className="text-sm font-medium text-gray-600 cursor-pointer hover:text-gray-900 list-none flex items-center gap-2">
          <span className="text-gray-400 group-open:rotate-90 transition-transform inline-block">▶</span>
          Advanced Settings
        </summary>
        <div className="mt-4 space-y-4 pl-4 border-l-2 border-gray-100">
          {/* Welcome Message */}
          <div>
            <label className="label">Welcome Message (for AI Voice Agent)</label>
            <textarea
              className="textarea"
              rows={2}
              placeholder="Hello! I'm calling to complete your KYC verification. Please have your Aadhaar and PAN card ready."
              value={builder.welcome_message}
              onChange={(e) => set('welcome_message', e.target.value)}
            />
          </div>

          {/* Completion Message */}
          <div>
            <label className="label">Completion Message</label>
            <textarea
              className="textarea"
              rows={2}
              placeholder="Thank you! Your documents have been submitted. We will notify you once verification is complete."
              value={builder.completion_message}
              onChange={(e) => set('completion_message', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Max Retry Attempts */}
            <div>
              <label className="label">Max Retry Attempts</label>
              <select
                className="select"
                value={builder.max_retry_attempts}
                onChange={(e) => set('max_retry_attempts', Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>{n} {n === 1 ? 'attempt' : 'attempts'}</option>
                ))}
              </select>
            </div>

            {/* Session Timeout */}
            <div>
              <label className="label">Session Timeout</label>
              <select
                className="select"
                value={builder.session_timeout_minutes}
                onChange={(e) => set('session_timeout_minutes', Number(e.target.value))}
              >
                {[15, 30, 45, 60, 90, 120, 240].map((n) => (
                  <option key={n} value={n}>{n >= 60 ? `${n / 60}h` : `${n} min`}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}
