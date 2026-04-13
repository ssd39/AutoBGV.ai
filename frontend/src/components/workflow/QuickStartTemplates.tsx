'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Zap, FileText, HelpCircle, ArrowRight, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchTemplates, createFromTemplate } from '@/store/workflowSlice';
import { CATEGORY_CONFIG } from '@/lib/constants';
import { WorkflowCategory } from '@/types';
import clsx from 'clsx';

interface QuickStartTemplatesProps {
  onSelect?: () => void;
}

export function QuickStartTemplates({ onSelect }: QuickStartTemplatesProps) {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { templates, isTemplatesLoaded } = useAppSelector((s) => ({
    templates: s.workflows.templates,
    isTemplatesLoaded: s.workflows.isTemplatesLoaded,
  }));

  useEffect(() => {
    if (!isTemplatesLoaded) {
      dispatch(fetchTemplates());
    }
  }, [dispatch, isTemplatesLoaded]);

  const handleUseTemplate = async (templateKey: string) => {
    const loadingToast = toast.loading('Creating workflow from template...');
    try {
      const result = await dispatch(createFromTemplate(templateKey)).unwrap();
      toast.dismiss(loadingToast);
      toast.success('Workflow created from template!');
      router.push(`/workflows/${result.id}/edit`);
      onSelect?.();
    } catch (e: unknown) {
      toast.dismiss(loadingToast);
      toast.error((e as Error).message || 'Failed to create from template');
    }
  };

  if (!isTemplatesLoaded) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="w-5 h-5 text-brand-500" />
          <h2 className="text-lg font-semibold text-gray-900">Quick-Start Templates</h2>
        </div>
        <p className="text-sm text-gray-500">
          Pre-configured workflows for common KYC, loan, and insurance use cases.
          Select one, customize it, and you&apos;re ready to go.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((template, i) => {
          const category = CATEGORY_CONFIG[template.category as WorkflowCategory];
          return (
            <motion.div
              key={template.template_key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className="card p-5 hover:shadow-card-hover hover:border-brand-200 transition-all duration-200 group"
            >
              {/* Category badge */}
              <div className="flex items-center justify-between mb-3">
                <span className={clsx('badge text-xs', category?.bg, category?.color)}>
                  {category?.icon} {category?.label}
                </span>
                <span className="text-xs text-gray-400">Template</span>
              </div>

              {/* Template name */}
              <h3 className="font-semibold text-gray-900 text-sm mb-2">{template.name}</h3>

              {/* Description */}
              <p className="text-xs text-gray-500 leading-relaxed mb-4 line-clamp-3">
                {template.description}
              </p>

              {/* Stats */}
              <div className="flex items-center gap-4 mb-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5 text-gray-400" />
                  <span className="font-medium text-gray-700">{template.document_count}</span> docs
                </span>
                <span className="flex items-center gap-1">
                  <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
                  <span className="font-medium text-gray-700">{template.question_count}</span> questions
                </span>
              </div>

              {/* Action */}
              <button
                onClick={() => handleUseTemplate(template.template_key)}
                className="w-full btn-primary text-xs py-2 group-hover:bg-brand-700"
              >
                Use This Template
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          );
        })}
      </div>

      {/* What happens note */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-xs text-blue-700 leading-relaxed">
          <strong>💡 How templates work:</strong> When you select a template, a new workflow is created in your account
          as a <strong>Draft</strong> with pre-configured documents and questions. You can edit everything before activating it.
        </p>
      </div>
    </div>
  );
}
