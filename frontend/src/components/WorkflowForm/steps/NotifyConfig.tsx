/**
 * Configuration form for Notify steps.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData } from '../../../types';
import { VariableHelper } from '../VariableHelper';

interface NotifyConfigProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Names of previous steps for variable helper */
  previousStepNames: string[];
}

/**
 * Form fields for configuring a notify step.
 */
export function NotifyConfig({
  stepIndex,
  previousStepNames,
}: NotifyConfigProps) {
  const { register, watch } = useFormContext<WorkflowFormData>();

  const channel = watch(`steps.${stepIndex}.config.channel`) as string;

  return (
    <div className="space-y-4">
      {/* Channel */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Channel
        </label>
        <select
          {...register(`steps.${stepIndex}.config.channel`)}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="discord">Discord</option>
        </select>
        <p className="mt-1 text-xs text-slate-400">
          More channels coming soon (Slack, Email)
        </p>
      </div>

      {/* Webhook URL */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Webhook URL <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          {...register(`steps.${stepIndex}.config.webhook_url`, {
            required: true,
          })}
          placeholder="https://discord.com/api/webhooks/... or {{secrets.DISCORD_WEBHOOK}}"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-slate-400">
          Discord webhook URL or use {'{{secrets.NAME}}'} for stored secrets
        </p>
      </div>

      {/* Message */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Message <span className="text-red-400">*</span>
        </label>
        <textarea
          {...register(`steps.${stepIndex}.config.message`, { required: true })}
          rows={3}
          placeholder="Workflow completed! Result: {{steps.previous.output}}"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
      </div>

      {/* Embed Toggle (Discord-specific) */}
      {channel === 'discord' && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id={`steps.${stepIndex}.config.embed`}
            {...register(`steps.${stepIndex}.config.embed`)}
            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800"
          />
          <label
            htmlFor={`steps.${stepIndex}.config.embed`}
            className="text-sm text-slate-300"
          >
            Send as embed (formatted card)
          </label>
        </div>
      )}

      {/* Variable Helper */}
      <VariableHelper stepNames={previousStepNames} />
    </div>
  );
}

export default NotifyConfig;
