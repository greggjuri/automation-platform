/**
 * Workflow detail page.
 *
 * Shows workflow configuration and execution history.
 */

import { useParams, Link } from 'react-router-dom';
import { useWorkflow, useExecutions, useExecuteWorkflow } from '../hooks';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage, StatusBadge } from '../components/common';
import { ExecutionList } from '../components/executions';

/**
 * Page component showing workflow details and execution history.
 *
 * Uses workflow ID from URL params.
 */
export function WorkflowDetailPage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const { data: workflow, isLoading, error, refetch } = useWorkflow(workflowId!);
  const {
    data: executionsData,
    isLoading: executionsLoading,
  } = useExecutions(workflowId!);
  const executeWorkflow = useExecuteWorkflow();

  const handleRunNow = () => {
    if (workflowId) {
      executeWorkflow.mutate({ workflowId });
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <LoadingSpinner label="Loading workflow..." />
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <ErrorMessage
          title="Failed to load workflow"
          message={error instanceof Error ? error.message : 'An error occurred'}
          onRetry={() => refetch()}
        />
      </Layout>
    );
  }

  if (!workflow) {
    return (
      <Layout>
        <ErrorMessage
          title="Workflow not found"
          message="The requested workflow does not exist."
        />
      </Layout>
    );
  }

  const executions = executionsData?.executions || [];

  return (
    <Layout>
      {/* Breadcrumb */}
      <nav className="mb-4">
        <Link
          to="/workflows"
          className="text-sm text-slate-400 hover:text-white transition-colors"
        >
          ← Back to Workflows
        </Link>
      </nav>

      {/* Workflow Header */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white">{workflow.name}</h1>
              <StatusBadge
                status={workflow.enabled ? 'success' : 'pending'}
                size="sm"
              />
            </div>
            {workflow.description && (
              <p className="mt-2 text-slate-400">{workflow.description}</p>
            )}
          </div>

          <div className="flex gap-2">
            <Link
              to={`/workflows/${workflowId}/edit`}
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md bg-slate-700 text-white hover:bg-slate-600 transition-colors"
            >
              <EditIcon />
              Edit
            </Link>
            <button
              onClick={handleRunNow}
              disabled={executeWorkflow.isPending}
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
            {executeWorkflow.isPending ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Running...
              </>
            ) : (
              <>
                <PlayIcon />
                Run Now
              </>
            )}
            </button>
          </div>
        </div>

        {/* Workflow Info */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InfoItem label="Trigger" value={formatTrigger(workflow.trigger)} />
          <InfoItem label="Steps" value={`${workflow.steps.length} step(s)`} />
          <InfoItem label="Created" value={formatDate(workflow.created_at)} />
          <InfoItem label="Updated" value={formatDate(workflow.updated_at)} />
        </div>

        {/* Execution Error */}
        {executeWorkflow.isError && (
          <div className="mt-4">
            <ErrorMessage
              title="Failed to start execution"
              message={
                executeWorkflow.error instanceof Error
                  ? executeWorkflow.error.message
                  : 'An error occurred'
              }
            />
          </div>
        )}

        {/* Execution Success */}
        {executeWorkflow.isSuccess && (
          <div className="mt-4 rounded-lg bg-green-500/10 border border-green-500/30 p-4">
            <p className="text-sm text-green-400">
              Execution started successfully.
              {executeWorkflow.data.execution_id && (
                <>
                  {' '}
                  <Link
                    to={`/workflows/${workflowId}/executions/${executeWorkflow.data.execution_id}`}
                    className="underline hover:text-green-300"
                  >
                    View execution
                  </Link>
                </>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Steps Section */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Steps</h2>
        <div className="space-y-3">
          {workflow.steps.map((step, index) => (
            <div
              key={step.step_id}
              className="flex items-center gap-4 p-3 bg-slate-700/50 rounded-lg"
            >
              <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-slate-600 text-xs font-medium text-slate-300">
                {index + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-white">{step.name}</p>
                <p className="text-sm text-slate-400">{step.type}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Execution History */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Execution History</h2>

        {executionsLoading ? (
          <LoadingSpinner size="sm" label="Loading executions..." />
        ) : (
          <ExecutionList executions={executions} workflowId={workflowId!} />
        )}
      </div>
    </Layout>
  );
}

/** Info item component */
function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-white">{value}</dd>
    </div>
  );
}

/** Format trigger for display */
function formatTrigger(trigger: { type: string; config?: Record<string, unknown> }): string {
  if (trigger.type === 'cron' && trigger.config?.schedule) {
    return `Schedule: ${trigger.config.schedule}`;
  }
  const labels: Record<string, string> = {
    webhook: 'Webhook',
    cron: 'Schedule',
    manual: 'Manual',
  };
  return labels[trigger.type] || trigger.type;
}

/** Format ISO date */
function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/** Play icon */
function PlayIcon() {
  return (
    <svg
      className="mr-2 h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="currentColor"
      viewBox="0 0 24 24"
    >
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

/** Edit icon */
function EditIcon() {
  return (
    <svg
      className="mr-2 h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  );
}

export default WorkflowDetailPage;
