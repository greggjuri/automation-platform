/**
 * Workflow detail page.
 *
 * Shows workflow configuration and execution history.
 */

import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useWorkflow, useExecutions, useExecuteWorkflow } from '../hooks';
import { useDeleteWorkflow } from '../hooks/useWorkflowMutations';
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
  const navigate = useNavigate();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const { data: workflow, isLoading, error, refetch } = useWorkflow(workflowId!);
  const {
    data: executionsData,
    isLoading: executionsLoading,
  } = useExecutions(workflowId!);
  const executeWorkflow = useExecuteWorkflow();
  const deleteWorkflow = useDeleteWorkflow();

  const handleRunNow = () => {
    if (workflowId) {
      executeWorkflow.mutate({ workflowId });
    }
  };

  const handleDelete = () => {
    if (!workflowId) return;

    deleteWorkflow.mutate(workflowId, {
      onSuccess: () => {
        toast.success('Workflow deleted successfully');
        navigate('/workflows');
      },
      onError: (err) => {
        toast.error(err instanceof Error ? err.message : 'Failed to delete workflow');
        setShowDeleteModal(false);
      },
    });
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
              onClick={() => setShowDeleteModal(true)}
              className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 transition-colors"
            >
              <TrashIcon />
              Delete
            </button>
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

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setShowDeleteModal(false)}
          />
          {/* Modal */}
          <div className="relative bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-white mb-2">
              Delete Workflow
            </h3>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete "{workflow.name}"? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleteWorkflow.isPending}
                className="px-4 py-2 text-sm font-medium rounded-md bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteWorkflow.isPending}
                className="px-4 py-2 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deleteWorkflow.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
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

/** Trash icon */
function TrashIcon() {
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
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

export default WorkflowDetailPage;
