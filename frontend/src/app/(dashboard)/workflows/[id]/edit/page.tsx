'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, AlertCircle } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  fetchWorkflow, loadWorkflowIntoBuilder,
  clearCurrentWorkflow,
} from '@/store/workflowSlice';
import { WorkflowBuilder } from '@/components/workflow/WorkflowBuilder';
import Link from 'next/link';

export default function EditWorkflowPage() {
  const params = useParams();
  const dispatch = useAppDispatch();
  const id = params.id as string;

  const { currentWorkflow: wf, isLoadingWorkflow, workflowError } = useAppSelector((s) => s.workflows);

  useEffect(() => {
    dispatch(fetchWorkflow(id)).then((action) => {
      if (action.payload) {
        dispatch(loadWorkflowIntoBuilder(action.payload as typeof wf & object));
      }
    });
    return () => { dispatch(clearCurrentWorkflow()); };
  }, [dispatch, id]);

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
        <p className="text-sm text-gray-500 mb-4">{workflowError}</p>
        <Link href="/workflows" className="btn-secondary">Back to Workflows</Link>
      </div>
    );
  }

  return <WorkflowBuilder mode="edit" workflowId={id} />;
}
