/**
 * Workflow creation page.
 *
 * Provides form UI for creating new workflows.
 */

import { useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Layout } from '../components/layout';
import { WorkflowForm } from '../components/WorkflowForm';
import { useCreateWorkflow } from '../hooks';
import type { WorkflowFormData } from '../types';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com';

/**
 * Page for creating a new workflow.
 */
export function WorkflowCreatePage() {
  const navigate = useNavigate();
  const createWorkflow = useCreateWorkflow();

  const handleSubmit = async (data: WorkflowFormData) => {
    try {
      const workflow = await createWorkflow.mutateAsync(data);
      toast.success('Workflow created successfully!');
      navigate(`/workflows/${workflow.workflow_id}`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to create workflow';
      toast.error(message);
      throw error; // Re-throw to keep form in error state
    }
  };

  const handleCancel = () => {
    navigate('/workflows');
  };

  return (
    <Layout>
      {/* Breadcrumb */}
      <nav className="mb-6">
        <Link
          to="/workflows"
          className="text-sm text-slate-400 hover:text-white transition-colors"
        >
          ← Back to Workflows
        </Link>
      </nav>

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Create Workflow</h1>
        <p className="mt-1 text-slate-400">
          Define a new automation workflow with triggers and steps.
        </p>
      </div>

      {/* Form */}
      <WorkflowForm
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={createWorkflow.isPending}
        apiBaseUrl={API_BASE_URL}
        submitLabel="Create Workflow"
      />
    </Layout>
  );
}

export default WorkflowCreatePage;
