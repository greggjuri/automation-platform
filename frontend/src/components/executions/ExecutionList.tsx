/**
 * Execution list component.
 *
 * Displays a list of workflow executions.
 */

import type { Execution } from '../../types';
import { ExecutionRow } from './ExecutionRow';

interface ExecutionListProps {
  /** Array of executions to display */
  executions: Execution[];
  /** Workflow ID for building links */
  workflowId: string;
}

/**
 * List of execution rows.
 *
 * @param props - Component props
 * @param props.executions - Executions to render
 * @param props.workflowId - Parent workflow ID
 *
 * @example
 * ```tsx
 * <ExecutionList executions={executions} workflowId="wf-123" />
 * ```
 */
export function ExecutionList({ executions, workflowId }: ExecutionListProps) {
  if (executions.length === 0) {
    return (
      <div className="text-center py-8">
        <svg
          className="mx-auto h-10 w-10 text-slate-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="mt-3 text-sm text-slate-400">No executions yet</p>
        <p className="text-xs text-slate-500">
          Run the workflow to see execution history
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-700">
      {executions.map((execution) => (
        <ExecutionRow
          key={execution.execution_id}
          execution={execution}
          workflowId={workflowId}
        />
      ))}
    </div>
  );
}

export default ExecutionList;
