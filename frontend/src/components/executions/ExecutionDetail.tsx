/**
 * Execution detail component.
 *
 * Shows full execution details including step results.
 */

import type { Execution, ExecutionStep } from '../../types';
import { StatusBadge } from '../common';

interface ExecutionDetailProps {
  /** Execution data to display */
  execution: Execution;
}

/**
 * Detailed view of an execution with step-by-step results.
 *
 * @param props - Component props
 * @param props.execution - Execution data
 *
 * @example
 * ```tsx
 * <ExecutionDetail execution={execution} />
 * ```
 */
export function ExecutionDetail({ execution }: ExecutionDetailProps) {
  const duration = calculateDuration(execution.started_at, execution.completed_at);

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Execution Summary</h2>
          <StatusBadge status={execution.status} />
        </div>

        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <dt className="text-sm text-slate-400">Execution ID</dt>
            <dd className="mt-1 text-sm font-mono text-white break-all">
              {execution.execution_id}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-400">Started</dt>
            <dd className="mt-1 text-sm text-white">
              {formatDateTime(execution.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-400">Completed</dt>
            <dd className="mt-1 text-sm text-white">
              {execution.completed_at
                ? formatDateTime(execution.completed_at)
                : 'In progress...'}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-400">Duration</dt>
            <dd className="mt-1 text-sm text-white">{duration}</dd>
          </div>
        </dl>

        {/* Error Message */}
        {execution.error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm font-medium text-red-400">Error</p>
            <p className="mt-1 text-sm text-red-300 font-mono">
              {execution.error}
            </p>
          </div>
        )}
      </div>

      {/* Steps Timeline */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Steps</h2>

        {execution.steps.length === 0 ? (
          <p className="text-sm text-slate-400">No step details available.</p>
        ) : (
          <div className="space-y-4">
            {execution.steps.map((step, index) => (
              <StepCard key={step.step_id} step={step} index={index} />
            ))}
          </div>
        )}
      </div>

      {/* Trigger Input */}
      {execution.trigger_input && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Trigger Input</h2>
          <pre className="p-4 bg-slate-900 rounded-lg overflow-x-auto text-sm text-slate-300 font-mono">
            {JSON.stringify(execution.trigger_input, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/** Single step card */
function StepCard({ step, index }: { step: ExecutionStep; index: number }) {
  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-4 bg-slate-700/30">
        <div className="flex items-center gap-3">
          <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-slate-600 text-xs font-medium text-slate-300">
            {index + 1}
          </span>
          <div>
            <p className="font-medium text-white">{step.name || step.step_id}</p>
            {step.type && <p className="text-xs text-slate-400">{step.type}</p>}
          </div>
        </div>
        <StatusBadge status={step.status} size="sm" />
      </div>

      {/* Step Details */}
      <div className="p-4 space-y-3">
        {/* Timing */}
        {step.started_at && (
          <div className="flex gap-4 text-xs text-slate-400">
            <span>Started: {formatDateTime(step.started_at)}</span>
            {step.completed_at && (
              <span>
                Duration: {calculateDuration(step.started_at, step.completed_at)}
              </span>
            )}
          </div>
        )}

        {/* Output */}
        {step.output && (
          <div>
            <p className="text-xs font-medium text-slate-400 mb-1">Output</p>
            <pre className="p-3 bg-slate-900 rounded text-xs text-slate-300 font-mono overflow-x-auto max-h-48">
              {typeof step.output === 'string'
                ? step.output
                : JSON.stringify(step.output, null, 2)}
            </pre>
          </div>
        )}

        {/* Error */}
        {step.error && (
          <div>
            <p className="text-xs font-medium text-red-400 mb-1">Error</p>
            <pre className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-300 font-mono overflow-x-auto">
              {step.error}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

/** Calculate duration between two timestamps */
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

export default ExecutionDetail;
