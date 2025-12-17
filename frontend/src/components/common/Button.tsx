/**
 * Glass button component.
 *
 * Reusable button with glass morphism effect and variants.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant of the button */
  variant?: ButtonVariant;
  /** Size variant */
  size?: ButtonSize;
  /** Whether the button is in a loading state */
  isLoading?: boolean;
  /** Icon to display before the label */
  leftIcon?: ReactNode;
  /** Icon to display after the label */
  rightIcon?: ReactNode;
  /** Button content */
  children: ReactNode;
}

/** Base glass button styles */
const baseStyles = `
  relative inline-flex items-center justify-center font-medium
  rounded-full transition-all duration-[400ms] ease-[cubic-bezier(0.25,1,0.5,1)]
  disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
  focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black
`;

/** Variant-specific styles */
const variantStyles: Record<ButtonVariant, string> = {
  primary: `
    bg-gradient-to-br from-white/5 via-white/12 to-white/5
    backdrop-blur-sm border border-white/10
    shadow-[inset_0_2px_2px_rgba(255,255,255,0.05),inset_0_-2px_2px_rgba(255,255,255,0.1),0_4px_2px_-2px_rgba(0,0,0,0.5)]
    text-[#e8e8e8] hover:text-white hover:scale-[0.975]
    hover:shadow-[inset_0_2px_2px_rgba(255,255,255,0.05),inset_0_-2px_2px_rgba(255,255,255,0.15),0_3px_1px_-2px_rgba(0,0,0,0.5)]
    focus:ring-white/30
  `,
  secondary: `
    bg-transparent backdrop-blur-sm
    border border-[#c0c0c0]/30
    text-[#c0c0c0] hover:text-[#e8e8e8] hover:border-[#c0c0c0]/50
    hover:scale-[0.975]
    focus:ring-[#c0c0c0]/30
  `,
  danger: `
    bg-gradient-to-br from-red-500/5 via-red-500/10 to-red-500/5
    backdrop-blur-sm border border-red-500/30
    text-red-400 hover:text-red-300 hover:border-red-500/50
    hover:scale-[0.975]
    focus:ring-red-500/30
  `,
  ghost: `
    bg-transparent border border-transparent
    text-[#c0c0c0] hover:text-[#e8e8e8]
    hover:bg-white/5 hover:border-white/10
    focus:ring-white/20
  `,
};

/** Size-specific styles */
const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-4 py-1.5 text-sm gap-1.5',
  md: 'px-6 py-2.5 text-sm gap-2',
  lg: 'px-8 py-3 text-base gap-2.5',
};

/**
 * Glass morphism button component.
 *
 * @example
 * ```tsx
 * <Button variant="primary" onClick={handleClick}>
 *   Save Changes
 * </Button>
 *
 * <Button variant="danger" size="sm" leftIcon={<TrashIcon />}>
 *   Delete
 * </Button>
 * ```
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      className = '',
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`.trim()}
        {...props}
      >
        {isLoading ? (
          <LoadingSpinner />
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

/** Simple loading spinner for button */
function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
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
  );
}

export default Button;
