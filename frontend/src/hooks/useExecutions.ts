/**
 * React Query hooks for execution data.
 *
 * Provides hooks for fetching executions and triggering new executions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Execution, ExecutionListResponse, ExecuteResponse } from '../types';

/** Query key factory for executions */
export const executionKeys = {
  all: (workflowId: string) => ['executions', workflowId] as const,
  detail: (workflowId: string, executionId: string) =>
    ['executions', workflowId, executionId] as const,
};

/**
 * Fetch executions for a workflow.
 *
 * @param workflowId - Workflow ID to fetch executions for
 * @param limit - Number of executions to fetch (default 20)
 * @returns React Query result with executions array
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useExecutions(workflowId);
 * ```
 */
export function useExecutions(workflowId: string, limit = 20) {
  return useQuery({
    queryKey: [...executionKeys.all(workflowId), { limit }],
    queryFn: async (): Promise<ExecutionListResponse> => {
      const response = await apiClient.get<ExecutionListResponse>(
        `/workflows/${workflowId}/executions`,
        { params: { limit } }
      );
      return response.data;
    },
    enabled: !!workflowId,
  });
}

/**
 * Fetch a single execution by ID.
 *
 * @param workflowId - Workflow ID
 * @param executionId - Execution ID to fetch
 * @returns React Query result with execution data
 *
 * @example
 * ```tsx
 * const { data: execution } = useExecution(workflowId, executionId);
 * ```
 */
export function useExecution(workflowId: string, executionId: string) {
  return useQuery({
    queryKey: executionKeys.detail(workflowId, executionId),
    queryFn: async (): Promise<Execution> => {
      const response = await apiClient.get<Execution>(
        `/workflows/${workflowId}/executions/${executionId}`
      );
      return response.data;
    },
    enabled: !!workflowId && !!executionId,
  });
}

/**
 * Mutation hook to trigger a workflow execution.
 *
 * @returns Mutation object with execute function
 *
 * @example
 * ```tsx
 * const { mutate: execute, isPending } = useExecuteWorkflow();
 * execute({ workflowId, triggerData: { foo: 'bar' } });
 * ```
 */
export function useExecuteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workflowId,
      triggerData = {},
    }: {
      workflowId: string;
      triggerData?: Record<string, unknown>;
    }): Promise<ExecuteResponse> => {
      const response = await apiClient.post<ExecuteResponse>(
        `/workflows/${workflowId}/execute`,
        { trigger_data: triggerData }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate executions list to show new execution
      queryClient.invalidateQueries({
        queryKey: executionKeys.all(variables.workflowId),
      });
    },
  });
}
