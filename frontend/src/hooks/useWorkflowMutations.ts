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

/** Response from toggle enabled endpoint */
interface ToggleEnabledResponse {
  workflow_id: string;
  enabled: boolean;
  message: string;
}

/**
 * Toggle workflow enabled/disabled status.
 *
 * @returns Mutation for toggling workflow enabled state
 *
 * @example
 * ```tsx
 * const toggleEnabled = useToggleWorkflowEnabled();
 * toggleEnabled.mutate(
 *   { workflowId: 'wf_123', enabled: false },
 *   { onSuccess: () => toast.success('Workflow disabled') }
 * );
 * ```
 */
export function useToggleWorkflowEnabled() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workflowId,
      enabled,
    }: {
      workflowId: string;
      enabled: boolean;
    }): Promise<ToggleEnabledResponse> => {
      const response = await apiClient.patch<ToggleEnabledResponse>(
        `/workflows/${workflowId}/enabled`,
        { enabled }
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(data.workflow_id) });
    },
  });
}
