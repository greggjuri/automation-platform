/**
 * Status badge component.
 *
 * Displays a colored badge indicating execution or step status.
 */

import type { ExecutionStatus, StepStatus } from '../../types';

type Status = ExecutionStatus | StepStatus;

interface StatusBadgeProps {
  /** Status value to display */
  status: Status;
  /** Optional size variant */
  size?: 'sm' | 'md';
}

/** Status to color mapping */
const statusColors: Record<Status, string> = {
  success: 'bg-green-500/20 text-green-400 border-green-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  running: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  pending: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  skipped: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

/** Size classes */
const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

/**
 * Colored badge showing execution/step status.
 *
 * @param props - Component props
 * @param props.status - Status to display
 * @param props.size - Size variant (default: 'md')
 *
 * @example
 * ```tsx
 * <StatusBadge status="success" />
 * <StatusBadge status="failed" size="sm" />
 * ```
 */
export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const colorClass = statusColors[status] || statusColors.pending;
  const sizeClass = sizeClasses[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${colorClass} ${sizeClass}`}
    >
      {status}
    </span>
  );
}

export default StatusBadge;
