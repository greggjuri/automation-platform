/**
 * Toggle switch component with glass styling.
 *
 * A styled toggle switch for enabling/disabling workflows.
 */

interface ToggleSwitchProps {
  /** Current enabled state */
  enabled: boolean;
  /** Callback when toggled */
  onChange: (enabled: boolean) => void;
  /** Whether the toggle is disabled */
  disabled?: boolean;
  /** Whether the toggle is in a loading state */
  isLoading?: boolean;
  /** Optional label displayed next to the toggle */
  label?: string;
  /** Optional aria-label for accessibility */
  ariaLabel?: string;
}

/**
 * Glass-styled toggle switch component.
 *
 * @example
 * ```tsx
 * <ToggleSwitch
 *   enabled={workflow.enabled}
 *   onChange={(enabled) => toggleEnabled.mutate({ workflowId, enabled })}
 *   isLoading={toggleEnabled.isPending}
 *   label="Enabled"
 * />
 * ```
 */
export function ToggleSwitch({
  enabled,
  onChange,
  disabled = false,
  isLoading = false,
  label,
  ariaLabel,
}: ToggleSwitchProps) {
  const isDisabled = disabled || isLoading;

  const handleClick = () => {
    if (!isDisabled) {
      onChange(!enabled);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div className="flex items-center gap-3">
      {label && (
        <span className="text-sm text-[#c0c0c0]">{label}</span>
      )}
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label={ariaLabel || label || 'Toggle'}
        disabled={isDisabled}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={`
          relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center
          rounded-full transition-all duration-300 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-white/30 focus:ring-offset-2 focus:ring-offset-black
          ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
          ${enabled
            ? 'bg-gradient-to-r from-green-500/30 to-green-400/20 border border-green-500/50'
            : 'bg-white/5 border border-white/10'
          }
        `}
      >
        {/* Track glow effect */}
        {enabled && (
          <span className="absolute inset-0 rounded-full bg-green-400/10 blur-sm" />
        )}

        {/* Thumb */}
        <span
          className={`
            relative inline-block h-4 w-4 transform rounded-full
            transition-all duration-300 ease-in-out
            shadow-[0_1px_3px_rgba(0,0,0,0.3)]
            ${enabled
              ? 'translate-x-6 bg-gradient-to-br from-green-400 to-green-500'
              : 'translate-x-1 bg-gradient-to-br from-[#c0c0c0] to-[#a0a0a0]'
            }
          `}
        >
          {/* Loading spinner inside thumb */}
          {isLoading && (
            <span className="absolute inset-0 flex items-center justify-center">
              <svg
                className="animate-spin h-3 w-3 text-white/80"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
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
            </span>
          )}
        </span>
      </button>
    </div>
  );
}

export default ToggleSwitch;
