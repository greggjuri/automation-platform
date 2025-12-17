/**
 * Trigger configuration component.
 *
 * Allows selecting trigger type and configuring type-specific options.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData } from '../../types';

interface TriggerConfigProps {
  /** Workflow ID (for showing webhook URL after save) */
  workflowId?: string;
  /** API base URL for webhook display */
  apiBaseUrl?: string;
}

const CRON_EXAMPLES = [
  { label: 'Every minute', value: 'rate(1 minute)' },
  { label: 'Every 5 minutes', value: 'rate(5 minutes)' },
  { label: 'Every hour', value: 'rate(1 hour)' },
  { label: 'Daily at midnight UTC', value: 'cron(0 0 * * ? *)' },
  { label: 'Daily at 9 AM UTC', value: 'cron(0 9 * * ? *)' },
  { label: 'Every Monday at 9 AM UTC', value: 'cron(0 9 ? * MON *)' },
];

/**
 * Trigger type selector and configuration.
 */
export function TriggerConfig({ workflowId, apiBaseUrl }: TriggerConfigProps) {
  const { register, watch, setValue } = useFormContext<WorkflowFormData>();

  const triggerType = watch('trigger.type');

  const webhookUrl = workflowId && apiBaseUrl
    ? `${apiBaseUrl}/webhook/${workflowId}`
    : null;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Trigger</h3>

      {/* Trigger Type */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Type
        </label>
        <select
          {...register('trigger.type')}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="manual">Manual</option>
          <option value="webhook">Webhook</option>
          <option value="cron">Schedule (Cron)</option>
        </select>
      </div>

      {/* Manual - No additional config */}
      {triggerType === 'manual' && (
        <p className="text-sm text-slate-400">
          This workflow will only run when manually triggered via the UI or API.
        </p>
      )}

      {/* Webhook - Show URL */}
      {triggerType === 'webhook' && (
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Webhook URL
          </label>
          {webhookUrl ? (
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={webhookUrl}
                className="flex-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-slate-300 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(webhookUrl)}
                className="px-3 py-2 bg-slate-700 text-slate-300 rounded-md hover:bg-slate-600 transition-colors"
                title="Copy to clipboard"
              >
                <CopyIcon />
              </button>
            </div>
          ) : (
            <p className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-slate-400 text-sm italic">
              Webhook URL will be generated after saving
            </p>
          )}
          <p className="mt-1 text-xs text-slate-400">
            POST to this URL to trigger the workflow. The request body will be
            available as {'{{trigger.body}}'}.
          </p>
        </div>
      )}

      {/* Cron - Schedule expression */}
      {triggerType === 'cron' && (
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Schedule Expression <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            {...register('trigger.config.schedule', {
              required: triggerType === 'cron',
            })}
            placeholder="rate(5 minutes) or cron(0 9 * * ? *)"
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="mt-1 text-xs text-slate-400">
            AWS EventBridge schedule expression.{' '}
            <a
              href="https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >
              Documentation
            </a>
          </p>

          {/* Quick Examples */}
          <div className="mt-3">
            <p className="text-xs text-slate-400 mb-2">Quick examples:</p>
            <div className="flex flex-wrap gap-2">
              {CRON_EXAMPLES.map((example) => (
                <button
                  key={example.value}
                  type="button"
                  onClick={() => setValue('trigger.config.schedule', example.value, { shouldDirty: true })}
                  className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
                >
                  {example.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CopyIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
      />
    </svg>
  );
}

export default TriggerConfig;
