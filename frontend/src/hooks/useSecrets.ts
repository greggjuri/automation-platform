/**
 * React Query hooks for secrets management.
 *
 * Provides hooks for fetching, creating, and deleting secrets from SSM.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { apiClient } from '../api/client';
import type {
  CreateSecretRequest,
  CreateSecretResponse,
  DeleteSecretResponse,
  SecretsListResponse,
} from '../types';

/** Query key factory for secrets */
export const secretKeys = {
  all: ['secrets'] as const,
};

/**
 * Fetch all secrets (metadata only).
 *
 * @returns React Query result with secrets array
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useSecrets();
 * if (isLoading) return <Loading />;
 * return <SecretsList secrets={data.secrets} />;
 * ```
 */
export function useSecrets() {
  return useQuery({
    queryKey: secretKeys.all,
    queryFn: async (): Promise<SecretsListResponse> => {
      const response = await apiClient.get<SecretsListResponse>('/secrets');
      return response.data;
    },
  });
}

/**
 * Create a new secret.
 *
 * @returns React Query mutation for creating secrets
 *
 * @example
 * ```tsx
 * const createMutation = useCreateSecret();
 * createMutation.mutate({ name: 'my_secret', value: '...', secret_type: 'custom' });
 * ```
 */
export function useCreateSecret() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateSecretRequest): Promise<CreateSecretResponse> => {
      const response = await apiClient.post<CreateSecretResponse>('/secrets', data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: secretKeys.all });
      toast.success(`Secret "${data.name}" created`);
    },
    onError: (error: Error & { response?: { data?: { message?: string } } }) => {
      const message = error.response?.data?.message || error.message;
      toast.error(`Failed to create secret: ${message}`);
    },
  });
}

/**
 * Delete a secret.
 *
 * @returns React Query mutation for deleting secrets
 *
 * @example
 * ```tsx
 * const deleteMutation = useDeleteSecret();
 * deleteMutation.mutate('my_secret');
 * ```
 */
export function useDeleteSecret() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string): Promise<DeleteSecretResponse> => {
      const response = await apiClient.delete<DeleteSecretResponse>(`/secrets/${name}`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: secretKeys.all });
      toast.success(`Secret "${data.name}" deleted`);
    },
    onError: (error: Error & { response?: { data?: { message?: string } } }) => {
      const message = error.response?.data?.message || error.message;
      toast.error(`Failed to delete secret: ${message}`);
    },
  });
}
