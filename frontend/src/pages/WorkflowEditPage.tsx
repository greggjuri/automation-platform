/**
 * Workflow edit page.
 *
 * Provides form UI for editing existing workflows.
 */

import { useNavigate, useParams, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage } from '../components/common';
import { WorkflowForm } from '../components/WorkflowForm';
import { useWorkflow, useUpdateWorkflow } from '../hooks';
import type { WorkflowFormData, Workflow } from '../types';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com';

/**
 * Convert workflow API response to form data.
 */
function workflowToFormData(workflow: Workflow): WorkflowFormData {
  return {
    name: workflow.name,
    description: workflow.description,
    enabled: workflow.enabled,
    trigger: {
      type: workflow.trigger.type as 'manual' | 'webhook' | 'cron',
      config: {
        schedule: (workflow.trigger.config?.schedule as string) || undefined,
      },
    },
    steps: workflow.steps.map((step) => ({
      step_id: step.step_id,
      name: step.name,
      type: step.type,
      // Cast to unknown first to avoid type narrowing issues
      config: step.config as unknown as WorkflowFormData['steps'][0]['config'],
    })),
  };
}

/**
 * Page for editing an existing workflow.
 */
export function WorkflowEditPage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();

  const { data: workflow, isLoading, error, refetch } = useWorkflow(workflowId!);
  const updateWorkflow = useUpdateWorkflow(workflowId!);

  const handleSubmit = async (data: WorkflowFormData) => {
    try {
      await updateWorkflow.mutateAsync(data);
      toast.success('Workflow updated successfully!');
      navigate(`/workflows/${workflowId}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to update workflow';
      toast.error(message);
      throw err; // Re-throw to keep form in error state
    }
  };

  const handleCancel = () => {
    navigate(`/workflows/${workflowId}`);
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

  const formData = workflowToFormData(workflow);

  return (
    <Layout>
      {/* Breadcrumb */}
      <nav className="mb-6">
        <Link
          to={`/workflows/${workflowId}`}
          className="text-sm text-slate-400 hover:text-white transition-colors"
        >
          ← Back to {workflow.name}
        </Link>
      </nav>

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Edit Workflow</h1>
        <p className="mt-1 text-slate-400">
          Modify the configuration for "{workflow.name}".
        </p>
      </div>

      {/* Form */}
      <WorkflowForm
        initialData={formData}
        workflowId={workflowId}
        apiBaseUrl={API_BASE_URL}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={updateWorkflow.isPending}
        submitLabel="Save Changes"
      />
    </Layout>
  );
}

export default WorkflowEditPage;
