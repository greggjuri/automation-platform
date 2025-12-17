/**
 * Helper component showing available template variables.
 *
 * Displays a collapsible panel with variable syntax help.
 */

import { useState } from 'react';

interface VariableHelperProps {
  /** Names of previous steps (for step output variables) */
  stepNames?: string[];
}

/**
 * Shows available template variables for interpolation.
 */
export function VariableHelper({ stepNames = [] }: VariableHelperProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const variables = [
    {
      name: '{{trigger.body}}',
      description: 'Webhook request body (JSON)',
    },
    {
      name: '{{trigger.headers}}',
      description: 'Webhook request headers',
    },
    {
      name: '{{trigger.query}}',
      description: 'Webhook query parameters',
    },
    ...stepNames.map((name) => ({
      name: `{{steps.${name}.output}}`,
      description: `Output from "${name}" step`,
    })),
    {
      name: '{{secrets.NAME}}',
      description: 'SSM parameter value (replace NAME)',
    },
  ];

  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-slate-400 hover:text-slate-300 transition-colors"
      >
        <InfoIcon />
        <span>Available variables</span>
        <ChevronIcon isExpanded={isExpanded} />
      </button>

      {isExpanded && (
        <div className="mt-2 p-3 bg-slate-700/50 rounded-md border border-slate-600">
          <p className="text-slate-400 mb-2">
            Use double braces to insert dynamic values:
          </p>
          <ul className="space-y-1">
            {variables.map((v) => (
              <li key={v.name} className="flex items-start gap-2">
                <code className="text-blue-400 font-mono whitespace-nowrap">
                  {v.name}
                </code>
                <span className="text-slate-400">- {v.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function InfoIcon() {
  return (
    <svg
      className="w-3.5 h-3.5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function ChevronIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <svg
      className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

export default VariableHelper;
