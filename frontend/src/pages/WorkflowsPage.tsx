/**
 * Workflows list page.
 *
 * Main page displaying all workflows with their status.
 */

import { Link } from 'react-router-dom';
import { useWorkflows } from '../hooks';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage, Button } from '../components/common';
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
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8e8e8]">Workflows</h1>
          <p className="mt-1 text-sm text-[#c0c0c0]">
            Manage and monitor your automation workflows
          </p>
        </div>
        <Link to="/workflows/new">
          <Button variant="primary" leftIcon={<PlusIcon />}>
            New Workflow
          </Button>
        </Link>
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

function PlusIcon() {
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
        d="M12 4v16m8-8H4"
      />
    </svg>
  );
}

export default WorkflowsPage;
