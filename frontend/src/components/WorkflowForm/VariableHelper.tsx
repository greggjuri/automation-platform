/**
 * Helper component showing available template variables.
 *
 * Displays a collapsible panel with context-aware variable hints
 * based on trigger type and previous steps.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import type { TriggerType, StepType } from '../../types';

interface VariableInfo {
  syntax: string;
  description: string;
}

interface PreviousStep {
  name: string;
  type: StepType;
}

interface VariableHelperProps {
  /** Current trigger type to show relevant variables */
  triggerType: TriggerType;
  /** Previous steps for step output variables */
  previousSteps: PreviousStep[];
}

/** Trigger-specific variables */
const TRIGGER_VARIABLES: Record<TriggerType, VariableInfo[]> = {
  manual: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("manual")' },
  ],
  webhook: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("webhook")' },
    { syntax: '{{trigger.payload}}', description: 'Webhook request body (JSON)' },
    { syntax: '{{trigger.headers}}', description: 'Request headers object' },
    { syntax: '{{trigger.query}}', description: 'Query string parameters' },
  ],
  cron: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("cron")' },
    { syntax: '{{trigger.scheduled_time}}', description: 'Scheduled execution time' },
  ],
  poll: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("poll")' },
    { syntax: '{{trigger.content_type}}', description: 'Content type (rss/atom/http)' },
    { syntax: '{{trigger.items}}', description: 'Array of feed items (RSS/Atom)' },
    { syntax: '{{trigger.items[0].title}}', description: 'First item title' },
    { syntax: '{{trigger.items[0].link}}', description: 'First item link' },
    { syntax: '{{trigger.items[0].guid}}', description: 'First item GUID' },
    { syntax: '{{trigger.items[0].summary}}', description: 'First item summary' },
    { syntax: '{{trigger.content}}', description: 'Raw content (HTTP poll)' },
    { syntax: '{{trigger.content_hash}}', description: 'Content hash (HTTP poll)' },
  ],
};

/** Step output hints by step type */
const STEP_OUTPUT_HINTS: Record<StepType, string[]> = {
  http_request: ['output.status', 'output.body', 'output.headers'],
  transform: ['output'],
  log: [], // No meaningful output
  notify: ['output.status_code'],
};

/** Trigger type display names */
const TRIGGER_TYPE_LABELS: Record<TriggerType, string> = {
  manual: 'Manual',
  webhook: 'Webhook',
  cron: 'Cron',
  poll: 'Poll',
};

/**
 * Builds step output variables for a given step.
 */
function getStepVariables(step: PreviousStep): VariableInfo[] {
  const hints = STEP_OUTPUT_HINTS[step.type] || [];

  if (hints.length === 0) {
    return [];
  }

  return hints.map((hint) => ({
    syntax: `{{steps.${step.name}.${hint}}}`,
    description: `${hint} from "${step.name}"`,
  }));
}

/**
 * Shows available template variables for interpolation.
 * Context-aware based on trigger type and previous steps.
 */
export function VariableHelper({
  triggerType,
  previousSteps,
}: VariableHelperProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const triggerVars = TRIGGER_VARIABLES[triggerType] || TRIGGER_VARIABLES.manual;
  const triggerLabel = TRIGGER_TYPE_LABELS[triggerType] || triggerType;

  // Build step variables
  const stepVars = previousSteps.flatMap(getStepVariables);

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard');
    } catch {
      toast.error('Failed to copy');
    }
  };

  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-[#c0c0c0] hover:text-[#e8e8e8] transition-colors"
      >
        <ChevronIcon isExpanded={isExpanded} />
        <span>Available Variables</span>
      </button>

      {isExpanded && (
        <div className="mt-2 p-4 bg-white/5 border border-white/10 rounded-lg space-y-4">
          {/* Trigger Variables */}
          <div>
            <h4 className="text-[#a0a0a0] font-medium mb-2">
              Trigger ({triggerLabel})
            </h4>
            <ul className="space-y-1">
              {triggerVars.map((v) => (
                <VariableRow
                  key={v.syntax}
                  variable={v}
                  onCopy={handleCopy}
                />
              ))}
            </ul>
          </div>

          {/* Step Variables */}
          <div>
            <h4 className="text-[#a0a0a0] font-medium mb-2">Previous Steps</h4>
            {stepVars.length > 0 ? (
              <ul className="space-y-1">
                {stepVars.map((v) => (
                  <VariableRow
                    key={v.syntax}
                    variable={v}
                    onCopy={handleCopy}
                  />
                ))}
              </ul>
            ) : (
              <p className="text-[#707070] italic">No previous steps</p>
            )}
          </div>

          {/* Secrets */}
          <div>
            <h4 className="text-[#a0a0a0] font-medium mb-2">Secrets</h4>
            <VariableRow
              variable={{
                syntax: '{{secrets.<name>}}',
                description: 'SSM parameter value',
              }}
              onCopy={handleCopy}
            />
            <p className="mt-1 text-[#707070] text-[10px]">
              Tip: Create secrets in Settings &gt; Secrets
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

interface VariableRowProps {
  variable: VariableInfo;
  onCopy: (text: string) => void;
}

function VariableRow({ variable, onCopy }: VariableRowProps) {
  return (
    <li className="flex items-center justify-between gap-2 group">
      <div className="flex items-center gap-2 min-w-0">
        <code className="text-blue-400 font-mono text-[11px] truncate">
          {variable.syntax}
        </code>
        <span className="text-[#707070] truncate hidden sm:inline">
          - {variable.description}
        </span>
      </div>
      <button
        type="button"
        onClick={() => onCopy(variable.syntax)}
        className="flex-shrink-0 p-1 text-[#707070] hover:text-[#e8e8e8] opacity-0 group-hover:opacity-100 transition-opacity"
        title="Copy to clipboard"
      >
        <CopyIcon />
      </button>
    </li>
  );
}

function ChevronIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <svg
      className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5l7 7-7 7"
      />
    </svg>
  );
}

function CopyIcon() {
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
        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
      />
    </svg>
  );
}

export default VariableHelper;
