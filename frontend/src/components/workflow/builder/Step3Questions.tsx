'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, ChevronDown, ChevronUp, GripVertical, HelpCircle, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import { addBuilderQuestion, updateBuilderQuestion, removeBuilderQuestion } from '@/store/workflowSlice';
import { QUESTION_TYPE_CONFIG } from '@/lib/constants';
import { QuestionType, BuilderQuestion } from '@/types';
import clsx from 'clsx';

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string; icon: string }[] = [
  { value: 'text',            label: 'Open Text',       icon: '📝' },
  { value: 'yes_no',          label: 'Yes / No',        icon: '✅' },
  { value: 'multiple_choice', label: 'Multiple Choice', icon: '📋' },
  { value: 'number',          label: 'Number',          icon: '🔢' },
  { value: 'date',            label: 'Date',            icon: '📅' },
];

const EXAMPLE_QUESTIONS = [
  { text: 'Is the address on your Aadhaar card the same as your current residential address?', type: 'yes_no' as QuestionType },
  { text: 'Are you a Politically Exposed Person (PEP) or a relative of a PEP?', type: 'yes_no' as QuestionType },
  { text: 'What is your primary source of income?', type: 'multiple_choice' as QuestionType, options: ['Salary / Employment', 'Business / Self-Employed', 'Investments / Rental Income', 'Pension / Retirement', 'Other'] },
  { text: 'What is your approximate monthly gross income (in INR)?', type: 'number' as QuestionType },
  { text: 'Do you have any existing EMIs or outstanding loans?', type: 'yes_no' as QuestionType },
  { text: 'What is your employment type?', type: 'multiple_choice' as QuestionType, options: ['Salaried - Private Sector', 'Salaried - Government / PSU', 'Self-Employed Professional', 'Self-Employed Business'] },
];

export function Step3Questions() {
  const dispatch = useAppDispatch();
  const builder = useAppSelector((s) => s.workflows.builder);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newOption, setNewOption] = useState<Record<string, string>>({});

  const addQuestion = (example?: typeof EXAMPLE_QUESTIONS[0]) => {
    dispatch(addBuilderQuestion({
      question_text: example?.text || '',
      question_type: example?.type || 'text',
      options: example?.options,
      is_required: true,
      order_index: builder.questions.length,
    }));
  };

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Customer Questions</h2>
        <p className="text-sm text-gray-500">
          Add questions to collect information from customers during the AI voice call.
          Questions are optional — you can skip this step if not needed.
        </p>
      </div>

      {/* Suggested Questions */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-gray-900">Quick Add — Suggested Questions</p>
          <span className="text-xs text-gray-400">Click to add</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {EXAMPLE_QUESTIONS.map((q, i) => {
            const alreadyAdded = builder.questions.some((bq) => bq.question_text === q.text);
            return (
              <button
                key={i}
                onClick={() => !alreadyAdded && addQuestion(q)}
                disabled={alreadyAdded}
                className={clsx(
                  'text-left p-3 rounded-lg border text-xs transition-all',
                  alreadyAdded
                    ? 'bg-green-50 border-green-200 text-green-700 cursor-default'
                    : 'border-gray-200 hover:border-brand-300 hover:bg-brand-50/50 cursor-pointer text-gray-700'
                )}
              >
                <div className="flex items-start gap-2">
                  <span>{QUESTION_TYPE_CONFIG[q.type]?.icon}</span>
                  <span className="leading-relaxed">{q.text}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Questions List */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-900">Workflow Questions</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {builder.questions.length} question{builder.questions.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button onClick={() => addQuestion()} className="btn-secondary btn-sm">
            <Plus className="w-3.5 h-3.5" /> Add Question
          </button>
        </div>

        <div className="p-3 space-y-2">
          {builder.questions.length === 0 ? (
            <div className="text-center py-10 text-sm text-gray-400 flex flex-col items-center gap-2">
              <HelpCircle className="w-8 h-8 text-gray-200" />
              <p>No questions added yet</p>
              <p className="text-xs">Use the suggestions above or click &quot;Add Question&quot;</p>
            </div>
          ) : (
            <AnimatePresence>
              {builder.questions.map((q) => (
                <QuestionItem
                  key={q._id}
                  question={q}
                  isExpanded={expandedId === q._id}
                  onToggle={() => setExpandedId(expandedId === q._id ? null : q._id)}
                  onRemove={() => dispatch(removeBuilderQuestion(q._id))}
                  onUpdate={(changes) => dispatch(updateBuilderQuestion({ _id: q._id, changes }))}
                  newOption={newOption[q._id] || ''}
                  onNewOptionChange={(v) => setNewOption((prev) => ({ ...prev, [q._id]: v }))}
                />
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Question Item ────────────────────────────────────────────────────────────

interface QuestionItemProps {
  question: BuilderQuestion;
  isExpanded: boolean;
  onToggle: () => void;
  onRemove: () => void;
  onUpdate: (changes: Partial<BuilderQuestion>) => void;
  newOption: string;
  onNewOptionChange: (v: string) => void;
}

function QuestionItem({
  question: q, isExpanded, onToggle, onRemove, onUpdate,
  newOption, onNewOptionChange,
}: QuestionItemProps) {
  const typeConfig = QUESTION_TYPE_CONFIG[q.question_type];

  const addOption = () => {
    if (!newOption.trim()) return;
    onUpdate({ options: [...(q.options || []), newOption.trim()] });
    onNewOptionChange('');
  };

  const removeOption = (idx: number) => {
    onUpdate({ options: q.options?.filter((_, i) => i !== idx) });
  };

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
        <span className="text-base flex-shrink-0">{typeConfig?.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-900 truncate">
            {q.question_text || <span className="text-gray-400 italic">No question text</span>}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-gray-400">{typeConfig?.label}</span>
            {q.is_required && <span className="text-xs text-red-400">Required</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={onToggle} className="w-6 h-6 flex items-center justify-center rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all">
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          <button onClick={onRemove} className="w-6 h-6 flex items-center justify-center rounded text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Expanded */}
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
              {/* Question Text */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Question Text</label>
                <textarea
                  className="textarea text-xs py-1.5"
                  rows={2}
                  placeholder="Enter your question..."
                  value={q.question_text}
                  onChange={(e) => onUpdate({ question_text: e.target.value })}
                />
              </div>

              {/* Type */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Answer Type</label>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                  {QUESTION_TYPE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => onUpdate({ question_type: opt.value })}
                      className={clsx(
                        'flex flex-col items-center gap-1 p-2 rounded-lg border text-center text-xs transition-all',
                        q.question_type === opt.value
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-gray-200 hover:border-gray-300 text-gray-600'
                      )}
                    >
                      <span>{opt.icon}</span>
                      <span className="leading-tight">{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Options for multiple choice */}
              {q.question_type === 'multiple_choice' && (
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1.5 block">Options</label>
                  <div className="space-y-1.5 mb-2">
                    {(q.options || []).map((opt, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <span className="text-xs text-gray-400 w-5 text-right">{idx + 1}.</span>
                        <input
                          type="text"
                          className="input text-xs py-1 flex-1"
                          value={opt}
                          onChange={(e) => {
                            const updated = [...(q.options || [])];
                            updated[idx] = e.target.value;
                            onUpdate({ options: updated });
                          }}
                        />
                        <button onClick={() => removeOption(idx)} className="text-gray-300 hover:text-red-500 transition-colors">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      className="input text-xs py-1 flex-1"
                      placeholder="Add option..."
                      value={newOption}
                      onChange={(e) => onNewOptionChange(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && addOption()}
                    />
                    <button onClick={addOption} className="btn-secondary btn-sm py-1">
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                  </div>
                </div>
              )}

              {/* Helper text */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Helper Text (optional)</label>
                <input
                  type="text"
                  className="input text-xs py-1.5"
                  placeholder="Additional context shown to the customer..."
                  value={q.helper_text || ''}
                  onChange={(e) => onUpdate({ helper_text: e.target.value })}
                />
              </div>

              {/* Required toggle */}
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-gray-600">Required Question</label>
                <button
                  onClick={() => onUpdate({ is_required: !q.is_required })}
                  className={clsx(
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                    q.is_required ? 'bg-brand-600' : 'bg-gray-300'
                  )}
                >
                  <span className={clsx(
                    'inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform',
                    q.is_required ? 'translate-x-4' : 'translate-x-1'
                  )} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
