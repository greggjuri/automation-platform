/**
 * Secrets management page.
 *
 * Page for managing secrets stored in SSM Parameter Store.
 */

import { useState } from 'react';
import { useSecrets, useCreateSecret, useDeleteSecret } from '../hooks/useSecrets';
import { Layout } from '../components/layout';
import { LoadingSpinner, ErrorMessage, Button } from '../components/common';
import { SecretCard, AddSecretModal, DeleteSecretModal } from '../components/secrets';
import type { CreateSecretRequest } from '../types';

/**
 * Page component for secrets management.
 *
 * Provides UI for listing, creating, and deleting secrets.
 */
export function SecretsPage() {
  const { data, isLoading, error, refetch } = useSecrets();
  const createMutation = useCreateSecret();
  const deleteMutation = useDeleteSecret();

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const handleCreateSecret = (data: CreateSecretRequest) => {
    createMutation.mutate(data, {
      onSuccess: () => {
        setIsAddModalOpen(false);
      },
    });
  };

  const handleDeleteSecret = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget, {
        onSuccess: () => {
          setDeleteTarget(null);
        },
      });
    }
  };

  return (
    <Layout>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8e8e8]">Secrets</h1>
          <p className="mt-1 text-sm text-[#c0c0c0]">
            Manage credentials and API keys for your workflows
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => setIsAddModalOpen(true)}
          leftIcon={<PlusIcon />}
        >
          Add Secret
        </Button>
      </div>

      {/* Info box */}
      <div className="mb-6 p-4 glass-card">
        <p className="text-sm text-[#c0c0c0]">
          Secrets are stored encrypted in AWS SSM Parameter Store. Use them in your
          workflows with{' '}
          <code className="px-1.5 py-0.5 bg-black/50 rounded text-blue-400 text-xs border border-white/10">
            {'{{secrets.secret_name}}'}
          </code>
        </p>
      </div>

      {isLoading && <LoadingSpinner label="Loading secrets..." />}

      {error && (
        <ErrorMessage
          title="Failed to load secrets"
          message={error instanceof Error ? error.message : 'An error occurred'}
          onRetry={() => refetch()}
        />
      )}

      {data && data.secrets.length === 0 && (
        <EmptyState onAddClick={() => setIsAddModalOpen(true)} />
      )}

      {data && data.secrets.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.secrets.map((secret) => (
            <SecretCard
              key={secret.name}
              secret={secret}
              onDelete={setDeleteTarget}
              isDeleting={deleteMutation.isPending && deleteTarget === secret.name}
            />
          ))}
        </div>
      )}

      {/* Add Secret Modal */}
      <AddSecretModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={handleCreateSecret}
        isSubmitting={createMutation.isPending}
      />

      {/* Delete Confirmation Modal */}
      <DeleteSecretModal
        isOpen={!!deleteTarget}
        secretName={deleteTarget || ''}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteSecret}
        isDeleting={deleteMutation.isPending}
      />
    </Layout>
  );
}

/** Empty state component */
function EmptyState({ onAddClick }: { onAddClick: () => void }) {
  return (
    <div className="text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white/5 border border-white/10 mb-4">
        <LockIcon />
      </div>
      <h3 className="text-lg font-medium text-[#e8e8e8] mb-1">No secrets yet</h3>
      <p className="text-sm text-[#c0c0c0] mb-4">
        Add your first secret to use in workflows
      </p>
      <Button variant="primary" onClick={onAddClick} leftIcon={<PlusIcon />}>
        Add Secret
      </Button>
    </div>
  );
}

function PlusIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 4v16m8-8H4"
      />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg
      className="w-8 h-8 text-[#c0c0c0]"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
      />
    </svg>
  );
}

export default SecretsPage;
