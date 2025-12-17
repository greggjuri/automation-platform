/**
 * Delete secret confirmation modal.
 *
 * Displays a confirmation dialog before deleting a secret.
 */

interface DeleteSecretModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Name of secret to delete */
  secretName: string;
  /** Callback to close modal */
  onClose: () => void;
  /** Callback when deletion is confirmed */
  onConfirm: () => void;
  /** Whether deletion is in progress */
  isDeleting?: boolean;
}

/**
 * Confirmation modal for deleting a secret.
 *
 * @param props - Component props
 */
export function DeleteSecretModal({
  isOpen,
  secretName,
  onClose,
  onConfirm,
  isDeleting,
}: DeleteSecretModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-sm bg-slate-800 rounded-lg border border-slate-700 shadow-xl">
          {/* Icon */}
          <div className="flex justify-center pt-6">
            <div className="p-3 bg-red-500/10 rounded-full">
              <WarningIcon />
            </div>
          </div>

          {/* Content */}
          <div className="p-6 text-center">
            <h3 className="text-lg font-semibold text-white mb-2">
              Delete Secret
            </h3>
            <p className="text-slate-400 text-sm">
              Are you sure you want to delete{' '}
              <span className="font-mono text-slate-300">{secretName}</span>?
            </p>
            <p className="mt-2 text-slate-500 text-xs">
              This action cannot be undone. Any workflows using this secret will fail.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 p-4 border-t border-slate-700">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 rounded-md hover:bg-slate-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Warning icon component */
function WarningIcon() {
  return (
    <svg className="w-8 h-8 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}

export default DeleteSecretModal;
