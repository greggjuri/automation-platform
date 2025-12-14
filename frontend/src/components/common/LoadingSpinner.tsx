/**
 * Loading spinner component.
 *
 * Displays an animated spinner for loading states.
 */

interface LoadingSpinnerProps {
  /** Optional size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Optional label text */
  label?: string;
}

/** Size classes for spinner */
const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
};

/**
 * Animated loading spinner.
 *
 * @param props - Component props
 * @param props.size - Size variant (default: 'md')
 * @param props.label - Optional accessibility label
 *
 * @example
 * ```tsx
 * <LoadingSpinner />
 * <LoadingSpinner size="lg" label="Loading workflows..." />
 * ```
 */
export function LoadingSpinner({ size = 'md', label }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8">
      <svg
        className={`animate-spin text-blue-500 ${sizeClasses[size]}`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      {label && (
        <p className="mt-2 text-sm text-slate-400">{label}</p>
      )}
    </div>
  );
}

export default LoadingSpinner;
