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
import { LoadingSpinner, ErrorMessage, StatusBadge, Button } from '../components/common';
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
          className="text-sm text-[#c0c0c0] hover:text-[#e8e8e8] transition-colors"
        >
          ← Back to Workflows
        </Link>
      </nav>

      {/* Workflow Header */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-[#e8e8e8]">{workflow.name}</h1>
              <StatusBadge
                status={workflow.enabled ? 'success' : 'pending'}
                size="sm"
              />
            </div>
            {workflow.description && (
              <p className="mt-2 text-[#c0c0c0]">{workflow.description}</p>
            )}
          </div>

          <div className="flex gap-2">
            <Link to={`/workflows/${workflowId}/edit`}>
              <Button variant="secondary" leftIcon={<EditIcon />}>
                Edit
              </Button>
            </Link>
            <Button
              variant="danger"
              onClick={() => setShowDeleteModal(true)}
              leftIcon={<TrashIcon />}
            >
              Delete
            </Button>
            <Button
              variant="primary"
              onClick={handleRunNow}
              isLoading={executeWorkflow.isPending}
              leftIcon={<PlayIcon />}
            >
              {executeWorkflow.isPending ? 'Running...' : 'Run Now'}
            </Button>
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
      <div className="glass-card p-6 mb-6">
        <h2 className="text-lg font-semibold text-[#e8e8e8] mb-4">Steps</h2>
        <div className="space-y-3">
          {workflow.steps.map((step, index) => (
            <div
              key={step.step_id}
              className="flex items-center gap-4 p-3 bg-white/[0.02] border border-white/5 rounded-lg"
            >
              <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-white/10 text-xs font-medium text-[#c0c0c0]">
                {index + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-[#e8e8e8]">{step.name}</p>
                <p className="text-sm text-[#c0c0c0]">{step.type}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Execution History */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-[#e8e8e8] mb-4">Execution History</h2>

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
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setShowDeleteModal(false)}
          />
          {/* Modal */}
          <div className="relative glass-card p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-[#e8e8e8] mb-2">
              Delete Workflow
            </h3>
            <p className="text-[#c0c0c0] mb-6">
              Are you sure you want to delete "{workflow.name}"? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteModal(false)}
                disabled={deleteWorkflow.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                isLoading={deleteWorkflow.isPending}
              >
                {deleteWorkflow.isPending ? 'Deleting...' : 'Delete'}
              </Button>
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
      <dt className="text-sm text-[#c0c0c0]">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[#e8e8e8]">{value}</dd>
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
      className="h-4 w-4"
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
      className="h-4 w-4"
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
      className="h-4 w-4"
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
