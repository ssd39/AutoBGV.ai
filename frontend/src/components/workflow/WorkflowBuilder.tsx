'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Check, ArrowLeft, ArrowRight, Save, Zap, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  setBuilderStep, setBuilderField, createWorkflow,
  fetchDocumentCatalog, fetchTemplates, resetBuilder,
} from '@/store/workflowSlice';
import { CATEGORY_CONFIG } from '@/lib/constants';
import { WorkflowCategory } from '@/types';
import { Step1BasicInfo } from './builder/Step1BasicInfo';
import { Step2Documents } from './builder/Step2Documents';
import { Step3Questions } from './builder/Step3Questions';
import { Step4Review } from './builder/Step4Review';
import { QuickStartTemplates } from './QuickStartTemplates';
import clsx from 'clsx';

const STEPS = [
  { id: 1, title: 'Basic Info',  desc: 'Name & category'      },
  { id: 2, title: 'Documents',  desc: 'Required documents'    },
  { id: 3, title: 'Questions',  desc: 'Customer questions'    },
  { id: 4, title: 'Review',     desc: 'Review & save'         },
];

interface WorkflowBuilderProps {
  mode: 'create' | 'edit';
  defaultTab?: string;
  workflowId?: string;
}

export function WorkflowBuilder({ mode, defaultTab = 'scratch', workflowId }: WorkflowBuilderProps) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { builder, isCatalogLoaded, isTemplatesLoaded } = useAppSelector((s) => ({
    builder: s.workflows.builder,
    isCatalogLoaded: s.workflows.isCatalogLoaded,
    isTemplatesLoaded: s.workflows.isTemplatesLoaded,
  }));

  const [activeTab, setActiveTab] = useState<string>(
    defaultTab === 'templates' ? 'templates' : 'scratch'
  );

  useEffect(() => {
    if (!isCatalogLoaded) dispatch(fetchDocumentCatalog());
    if (!isTemplatesLoaded) dispatch(fetchTemplates());
  }, [dispatch, isCatalogLoaded, isTemplatesLoaded]);

  const currentStep = builder.step;

  const validateStep = (step: number): boolean => {
    if (step === 1) {
      if (!builder.name.trim()) {
        toast.error('Workflow name is required');
        return false;
      }
      if (builder.name.length < 3) {
        toast.error('Name must be at least 3 characters');
        return false;
      }
    }
    if (step === 2) {
      if (builder.documents.length === 0) {
        toast.error('Add at least one document requirement');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (!validateStep(currentStep)) return;
    dispatch(setBuilderStep(currentStep + 1));
  };

  const handleBack = () => {
    dispatch(setBuilderStep(currentStep - 1));
  };

  const handleSave = async () => {
    if (!validateStep(currentStep)) return;
    try {
      const result = await dispatch(createWorkflow()).unwrap();
      toast.success('Workflow created successfully!');
      router.push(`/workflows/${result.id}`);
    } catch (e: unknown) {
      toast.error((e as Error).message || 'Failed to save workflow');
    }
  };

  // If in template mode, show templates first
  if (mode === 'create' && activeTab === 'templates') {
    return (
      <div className="max-w-5xl mx-auto">
        {/* Tab switcher */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1 w-fit mb-6">
          <button
            onClick={() => setActiveTab('scratch')}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 text-gray-500 hover:text-gray-700"
          >
            <Plus className="w-4 h-4 inline mr-1.5" />
            Build from Scratch
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 bg-white text-gray-900 shadow-sm"
          >
            <Zap className="w-4 h-4 inline mr-1.5" />
            Quick-Start Templates
          </button>
        </div>

        <QuickStartTemplates onSelect={() => { setActiveTab('scratch'); }} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Tab switcher (only in create mode) */}
      {mode === 'create' && (
        <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1 w-fit mb-6">
          <button
            onClick={() => setActiveTab('scratch')}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
              activeTab === 'scratch'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            )}
          >
            <Plus className="w-4 h-4 inline mr-1.5" />
            Build from Scratch
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
              activeTab === 'templates'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            )}
          >
            <Zap className="w-4 h-4 inline mr-1.5" />
            Quick-Start Templates
          </button>
        </div>
      )}

      {/* Step Progress */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between">
          {STEPS.map((step, idx) => (
            <div key={step.id} className="flex items-center flex-1">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    if (step.id < currentStep) dispatch(setBuilderStep(step.id));
                  }}
                  className={clsx(
                    'step-indicator',
                    step.id < currentStep ? 'completed cursor-pointer hover:opacity-80' :
                    step.id === currentStep ? 'active' : 'pending'
                  )}
                  disabled={step.id > currentStep}
                >
                  {step.id < currentStep ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <span>{step.id}</span>
                  )}
                </button>
                <div className="hidden sm:block">
                  <p className={clsx(
                    'text-sm font-medium',
                    step.id === currentStep ? 'text-gray-900' :
                    step.id < currentStep ? 'text-brand-600' : 'text-gray-400'
                  )}>
                    {step.title}
                  </p>
                  <p className="text-xs text-gray-400">{step.desc}</p>
                </div>
              </div>
              {idx < STEPS.length - 1 && (
                <div className={clsx(
                  'flex-1 h-0.5 mx-4 rounded-full',
                  step.id < currentStep ? 'bg-brand-400' : 'bg-gray-200'
                )} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {currentStep === 1 && <Step1BasicInfo />}
          {currentStep === 2 && <Step2Documents />}
          {currentStep === 3 && <Step3Questions />}
          {currentStep === 4 && <Step4Review />}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
        <button
          onClick={currentStep === 1 ? () => router.push('/workflows') : handleBack}
          className="btn-secondary"
        >
          <ArrowLeft className="w-4 h-4" />
          {currentStep === 1 ? 'Cancel' : 'Back'}
        </button>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            Step {currentStep} of {STEPS.length}
          </span>

          {currentStep < STEPS.length ? (
            <button onClick={handleNext} className="btn-primary">
              Next
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSave}
              disabled={builder.isSaving}
              className="btn-primary"
            >
              {builder.isSaving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Workflow
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
