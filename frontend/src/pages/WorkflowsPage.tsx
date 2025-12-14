/**
 * Workflows list page.
 *
 * Main page displaying all workflows with their status.
 */

import { useWorkflows } from '../hooks';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage } from '../components/common';
import { WorkflowList } from '../components/workflows';

/**
 * Page component showing all workflows.
 *
 * Fetches workflows from API and displays them in a grid.
 */
export function WorkflowsPage() {
  const { data, isLoading, error, refetch } = useWorkflows();

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Workflows</h1>
        <p className="mt-1 text-sm text-slate-400">
          Manage and monitor your automation workflows
        </p>
      </div>

      {isLoading && <LoadingSpinner label="Loading workflows..." />}

      {error && (
        <ErrorMessage
          title="Failed to load workflows"
          message={error instanceof Error ? error.message : 'An error occurred'}
          onRetry={() => refetch()}
        />
      )}

      {data && <WorkflowList workflows={data.workflows} />}
    </Layout>
  );
}

export default WorkflowsPage;
