/**
 * Workflow list component.
 *
 * Displays a grid of workflow cards.
 */

import type { Workflow } from '../../types';
import { WorkflowCard } from './WorkflowCard';

interface WorkflowListProps {
  /** Array of workflows to display */
  workflows: Workflow[];
}

/**
 * Grid of workflow cards.
 *
 * @param props - Component props
 * @param props.workflows - Workflows to render
 *
 * @example
 * ```tsx
 * <WorkflowList workflows={workflows} />
 * ```
 */
export function WorkflowList({ workflows }: WorkflowListProps) {
  if (workflows.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-slate-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium text-slate-300">No workflows</h3>
        <p className="mt-2 text-sm text-slate-500">
          Get started by creating your first workflow.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {workflows.map((workflow) => (
        <WorkflowCard key={workflow.workflow_id} workflow={workflow} />
      ))}
    </div>
  );
}

export default WorkflowList;
