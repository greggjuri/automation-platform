/**
 * Workflow card component.
 *
 * Displays a single workflow summary in a card format with glass styling.
 */

import { Link } from 'react-router-dom';
import type { Workflow } from '../../types';
import { StatusBadge } from '../common';

interface WorkflowCardProps {
  /** Workflow data to display */
  workflow: Workflow;
}

/**
 * Card displaying workflow summary with link to detail page.
 *
 * @param props - Component props
 * @param props.workflow - Workflow data
 *
 * @example
 * ```tsx
 * <WorkflowCard workflow={workflow} />
 * ```
 */
export function WorkflowCard({ workflow }: WorkflowCardProps) {
  const triggerLabel = getTriggerLabel(workflow.trigger?.type);
  const stepCount = workflow.steps?.length ?? 0;

  return (
    <Link
      to={`/workflows/${workflow.workflow_id}`}
      className="block glass-card p-6 hover:bg-white/[0.05] hover:border-white/[0.15]"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-[#e8e8e8] truncate">
            {workflow.name}
          </h3>
          {workflow.description && (
            <p className="mt-1 text-sm text-[#c0c0c0] line-clamp-2">
              {workflow.description}
            </p>
          )}
        </div>
        <StatusBadge status={workflow.enabled ? 'success' : 'pending'} size="sm" />
      </div>

      <div className="mt-4 flex items-center gap-4 text-sm text-[#c0c0c0]">
        <div className="flex items-center gap-1.5">
          <TriggerIcon />
          <span>{triggerLabel}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <StepsIcon />
          <span>{stepCount} step{stepCount !== 1 ? 's' : ''}</span>
        </div>
      </div>

      <div className="mt-3 text-xs text-[#c0c0c0]/60">
        Updated {formatDate(workflow.updated_at)}
      </div>
    </Link>
  );
}

/** Get human-readable trigger type label */
function getTriggerLabel(type?: string): string {
  if (!type) return 'Unknown';
  const labels: Record<string, string> = {
    webhook: 'Webhook',
    cron: 'Schedule',
    manual: 'Manual',
  };
  return labels[type] || type;
}

/** Format ISO date to relative or short date */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

/** Trigger icon SVG */
function TriggerIcon() {
  return (
    <svg
      className="w-4 h-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 10V3L4 14h7v7l9-11h-7z"
      />
    </svg>
  );
}

/** Steps icon SVG */
function StepsIcon() {
  return (
    <svg
      className="w-4 h-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h16"
      />
    </svg>
  );
}

export default WorkflowCard;
