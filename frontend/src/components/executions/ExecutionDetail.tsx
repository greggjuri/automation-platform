/**
 * Execution detail component.
 *
 * Shows full execution details including step results.
 */

import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import type { Execution, ExecutionStep, ExecuteResponse } from '../../types';
import { StatusBadge, Button } from '../common';
import { apiClient } from '../../api/client';
import { executionKeys } from '../../hooks/useExecutions';

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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const duration = calculateDuration(execution.started_at, execution.finished_at);

  // Retry mutation
  const retryMutation = useMutation({
    mutationFn: async (): Promise<ExecuteResponse> => {
      const response = await apiClient.post<ExecuteResponse>(
        `/workflows/${execution.workflow_id}/execute`,
        { trigger_data: execution.trigger_data || {} }
      );
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Workflow re-triggered successfully');
      // Invalidate executions list
      queryClient.invalidateQueries({
        queryKey: executionKeys.all(execution.workflow_id),
      });
      // Navigate to the new execution
      navigate(
        `/workflows/${execution.workflow_id}/executions/${data.execution_id}`
      );
    },
  });

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[#e8e8e8]">
            Execution Summary
          </h2>
          <div className="flex items-center gap-3">
            {execution.status === 'failed' && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => retryMutation.mutate()}
                isLoading={retryMutation.isPending}
                leftIcon={<RetryIcon />}
              >
                Retry
              </Button>
            )}
            <StatusBadge status={execution.status} />
          </div>
        </div>

        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <dt className="text-sm text-[#c0c0c0]">Execution ID</dt>
            <dd className="mt-1 text-sm font-mono text-[#e8e8e8] break-all">
              {execution.execution_id}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-[#c0c0c0]">Started</dt>
            <dd className="mt-1 text-sm text-[#e8e8e8]">
              {formatDateTime(execution.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-[#c0c0c0]">Completed</dt>
            <dd className="mt-1 text-sm text-[#e8e8e8]">
              {execution.finished_at
                ? formatDateTime(execution.finished_at)
                : 'In progress...'}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-[#c0c0c0]">Duration</dt>
            <dd className="mt-1 text-sm text-[#e8e8e8]">{duration}</dd>
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
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-[#e8e8e8] mb-4">Steps</h2>

        {execution.steps.length === 0 ? (
          <p className="text-sm text-[#c0c0c0]">No step details available.</p>
        ) : (
          <div className="space-y-4">
            {execution.steps.map((step, index) => (
              <StepCard key={step.step_id} step={step} index={index} />
            ))}
          </div>
        )}
      </div>

      {/* Trigger Data */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-[#e8e8e8] mb-4">
          Trigger Data
        </h2>
        {isTriggerDataEmpty(execution.trigger_data) ? (
          <p className="text-sm text-[#c0c0c0] italic">
            {execution.trigger_type === 'manual'
              ? 'Manual trigger (no data)'
              : 'No trigger data available'}
          </p>
        ) : (
          <pre className="p-4 bg-black/50 rounded-lg overflow-x-auto text-sm text-[#c0c0c0] font-mono border border-white/5">
            {JSON.stringify(execution.trigger_data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

/** Single step card with failure highlighting */
function StepCard({ step, index }: { step: ExecutionStep; index: number }) {
  const isFailed = step.status === 'failed';

  return (
    <div
      className={`border rounded-lg overflow-hidden transition-colors ${
        isFailed
          ? 'border-red-500/50 bg-red-500/5'
          : 'border-white/10 bg-white/[0.02]'
      }`}
    >
      <div
        className={`flex items-center justify-between p-4 ${
          isFailed ? 'bg-red-500/10' : 'bg-white/[0.03]'
        }`}
      >
        <div className="flex items-center gap-3">
          <span
            className={`flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full text-xs font-medium ${
              isFailed
                ? 'bg-red-500/20 text-red-400'
                : 'bg-white/10 text-[#c0c0c0]'
            }`}
          >
            {index + 1}
          </span>
          <div>
            <p className="font-medium text-[#e8e8e8]">
              {step.name || step.step_id}
            </p>
            {step.type && (
              <p className="text-xs text-[#c0c0c0]">{step.type}</p>
            )}
          </div>
        </div>
        <StatusBadge status={step.status} size="sm" />
      </div>

      {/* Step Details */}
      <div className="p-4 space-y-3">
        {/* Timing */}
        {step.started_at && (
          <div className="flex gap-4 text-xs text-[#c0c0c0]">
            <span>Started: {formatDateTime(step.started_at)}</span>
            {step.finished_at && (
              <span>
                Duration: {calculateDuration(step.started_at, step.finished_at)}
              </span>
            )}
          </div>
        )}

        {/* Output */}
        {step.output && (
          <div>
            <p className="text-xs font-medium text-[#c0c0c0] mb-1">Output</p>
            <pre className="p-3 bg-black/50 rounded text-xs text-[#c0c0c0] font-mono overflow-x-auto max-h-48 border border-white/5">
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

/** Retry icon */
function RetryIcon() {
  return (
    <svg
      className="w-4 h-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}

/** Check if trigger data is empty or null */
function isTriggerDataEmpty(data?: Record<string, unknown>): boolean {
  if (!data) return true;
  return Object.keys(data).length === 0;
}

/** Calculate duration between two timestamps */
function calculateDuration(
  startedAt: string,
  completedAt?: string | null
): string {
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
