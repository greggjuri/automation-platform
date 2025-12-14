/**
 * React Query hooks for workflow data.
 *
 * Provides hooks for fetching and caching workflow data from the API.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Workflow, WorkflowListResponse } from '../types';

/** Query key factory for workflows */
export const workflowKeys = {
  all: ['workflows'] as const,
  detail: (id: string) => ['workflows', id] as const,
};

/**
 * Fetch all workflows.
 *
 * @returns React Query result with workflows array
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useWorkflows();
 * if (isLoading) return <Loading />;
 * return <WorkflowList workflows={data.workflows} />;
 * ```
 */
export function useWorkflows() {
  return useQuery({
    queryKey: workflowKeys.all,
    queryFn: async (): Promise<WorkflowListResponse> => {
      const response = await apiClient.get<WorkflowListResponse>('/workflows');
      return response.data;
    },
  });
}

/**
 * Fetch a single workflow by ID.
 *
 * @param id - Workflow ID to fetch
 * @returns React Query result with workflow data
 *
 * @example
 * ```tsx
 * const { data: workflow, isLoading } = useWorkflow(workflowId);
 * ```
 */
export function useWorkflow(id: string) {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: async (): Promise<Workflow> => {
      const response = await apiClient.get<Workflow>(`/workflows/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}
