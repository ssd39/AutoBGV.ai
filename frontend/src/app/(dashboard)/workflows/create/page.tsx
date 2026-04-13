'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAppDispatch } from '@/store';
import { resetBuilder } from '@/store/workflowSlice';
import { WorkflowBuilder } from '@/components/workflow/WorkflowBuilder';
import { Loader2 } from 'lucide-react';

function CreateWorkflowContent() {
  const dispatch = useAppDispatch();
  const searchParams = useSearchParams();
  const defaultTab = searchParams.get('tab') || 'scratch';

  useEffect(() => {
    dispatch(resetBuilder());
  }, [dispatch]);

  return <WorkflowBuilder mode="create" defaultTab={defaultTab} />;
}

export default function CreateWorkflowPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
        </div>
      }
    >
      <CreateWorkflowContent />
    </Suspense>
  );
}
