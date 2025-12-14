/**
 * Execution detail page.
 *
 * Shows complete execution information with step results.
 */

import { useParams, Link } from 'react-router-dom';
import { useExecution, useWorkflow } from '../hooks';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage } from '../components/common';
import { ExecutionDetail } from '../components/executions';

/**
 * Page component showing execution details.
 *
 * Uses workflow ID and execution ID from URL params.
 */
export function ExecutionDetailPage() {
  const { workflowId, executionId } = useParams<{
    workflowId: string;
    executionId: string;
  }>();

  const {
    data: execution,
    isLoading,
    error,
    refetch,
  } = useExecution(workflowId!, executionId!);

  const { data: workflow } = useWorkflow(workflowId!);

  if (isLoading) {
    return (
      <Layout>
        <LoadingSpinner label="Loading execution..." />
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <ErrorMessage
          title="Failed to load execution"
          message={error instanceof Error ? error.message : 'An error occurred'}
          onRetry={() => refetch()}
        />
      </Layout>
    );
  }

  if (!execution) {
    return (
      <Layout>
        <ErrorMessage
          title="Execution not found"
          message="The requested execution does not exist."
        />
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Breadcrumb */}
      <nav className="mb-4 flex items-center gap-2 text-sm text-slate-400">
        <Link to="/workflows" className="hover:text-white transition-colors">
          Workflows
        </Link>
        <span>/</span>
        <Link
          to={`/workflows/${workflowId}`}
          className="hover:text-white transition-colors"
        >
          {workflow?.name || 'Workflow'}
        </Link>
        <span>/</span>
        <span className="text-slate-500">Execution</span>
      </nav>

      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Execution Details</h1>
        <p className="mt-1 text-sm text-slate-400">
          {workflow?.name || 'Workflow'} execution from{' '}
          {formatDateTime(execution.started_at)}
        </p>
      </div>

      {/* Execution Detail Component */}
      <ExecutionDetail execution={execution} />
    </Layout>
  );
}

/** Format ISO date to readable datetime */
function formatDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default ExecutionDetailPage;
