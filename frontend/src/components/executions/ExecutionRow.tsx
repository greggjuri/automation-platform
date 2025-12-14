/**
 * Execution row component.
 *
 * Displays a single execution in a table row format.
 */

import { Link } from 'react-router-dom';
import type { Execution } from '../../types';
import { StatusBadge } from '../common';

interface ExecutionRowProps {
  /** Execution data to display */
  execution: Execution;
  /** Workflow ID for building links */
  workflowId: string;
}

/**
 * Table row showing execution summary.
 *
 * @param props - Component props
 * @param props.execution - Execution data
 * @param props.workflowId - Parent workflow ID
 *
 * @example
 * ```tsx
 * <ExecutionRow execution={execution} workflowId="wf-123" />
 * ```
 */
export function ExecutionRow({ execution, workflowId }: ExecutionRowProps) {
  const duration = calculateDuration(execution.started_at, execution.completed_at);

  return (
    <Link
      to={`/workflows/${workflowId}/executions/${execution.execution_id}`}
      className="flex items-center justify-between p-4 hover:bg-slate-700/50 transition-colors rounded-lg"
    >
      <div className="flex items-center gap-4">
        <StatusBadge status={execution.status} size="sm" />
        <div>
          <p className="text-sm font-medium text-white">
            {execution.execution_id.slice(0, 8)}...
          </p>
          <p className="text-xs text-slate-400">
            {formatDateTime(execution.started_at)}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="text-right">
          <p className="text-slate-400">Duration</p>
          <p className="text-white">{duration}</p>
        </div>
        <ChevronRightIcon />
      </div>
    </Link>
  );
}

/** Calculate execution duration */
function calculateDuration(startedAt: string, completedAt?: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const durationMs = end - start;

  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }

  const seconds = Math.floor(durationMs / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

/** Format ISO date to readable datetime */
function formatDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
}

/** Chevron right icon */
function ChevronRightIcon() {
  return (
    <svg
      className="w-5 h-5 text-slate-500"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5l7 7-7 7"
      />
    </svg>
  );
}

export default ExecutionRow;
