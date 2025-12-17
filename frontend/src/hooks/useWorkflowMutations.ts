/**
 * React Query mutation hooks for workflow create/update operations.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Workflow, WorkflowFormData } from '../types';
import { workflowKeys } from './useWorkflows';

/**
 * Create a new workflow.
 *
 * @returns Mutation for creating workflows
 *
 * @example
 * ```tsx
 * const createWorkflow = useCreateWorkflow();
 * createWorkflow.mutate(formData, {
 *   onSuccess: (workflow) => navigate(`/workflows/${workflow.workflow_id}`),
 * });
 * ```
 */
export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: WorkflowFormData): Promise<Workflow> => {
      const response = await apiClient.post<Workflow>('/workflows', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
}

/**
 * Update an existing workflow.
 *
 * @param workflowId - ID of workflow to update
 * @returns Mutation for updating the workflow
 *
 * @example
 * ```tsx
 * const updateWorkflow = useUpdateWorkflow(workflowId);
 * updateWorkflow.mutate(formData, {
 *   onSuccess: () => navigate(`/workflows/${workflowId}`),
 * });
 * ```
 */
export function useUpdateWorkflow(workflowId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<WorkflowFormData>): Promise<Workflow> => {
      const response = await apiClient.put<Workflow>(
        `/workflows/${workflowId}`,
        data
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
    },
  });
}

/**
 * Delete a workflow.
 *
 * @returns Mutation for deleting workflows
 */
export function useDeleteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (workflowId: string): Promise<void> => {
      await apiClient.delete(`/workflows/${workflowId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
}
