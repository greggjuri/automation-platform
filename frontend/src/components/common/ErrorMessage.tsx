/**
 * Error message component.
 *
 * Displays error messages with optional retry functionality.
 */

interface ErrorMessageProps {
  /** Error message to display */
  message: string;
  /** Optional title (default: 'Error') */
  title?: string;
  /** Optional retry callback */
  onRetry?: () => void;
}

/**
 * Error display with optional retry button.
 *
 * @param props - Component props
 * @param props.message - Error message text
 * @param props.title - Optional title heading
 * @param props.onRetry - Optional callback for retry button
 *
 * @example
 * ```tsx
 * <ErrorMessage message="Failed to load data" />
 * <ErrorMessage
 *   title="Connection Error"
 *   message="Unable to reach the server"
 *   onRetry={() => refetch()}
 * />
 * ```
 */
export function ErrorMessage({ message, title = 'Error', onRetry }: ErrorMessageProps) {
  return (
    <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-6">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-6 w-6 text-red-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-400">{title}</h3>
          <p className="mt-1 text-sm text-red-300">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-4 inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-red-500/20 text-red-300 hover:bg-red-500/30 transition-colors"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ErrorMessage;
