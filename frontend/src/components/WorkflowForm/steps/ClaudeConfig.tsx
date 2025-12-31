/**
 * Configuration form for Claude AI steps.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData, TriggerType, StepType } from '../../../types';
import { VariableHelper } from '../VariableHelper';

interface PreviousStep {
  name: string;
  type: StepType;
}

interface ClaudeConfigProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Current trigger type */
  triggerType: TriggerType;
  /** Previous steps with name and type */
  previousSteps: PreviousStep[];
}

const MODEL_OPTIONS = [
  { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (Fast, cheap)' },
  { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (Newer fast)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Most capable)' },
];

/**
 * Form fields for configuring a Claude AI step.
 */
export function ClaudeConfig({
  stepIndex,
  triggerType,
  previousSteps,
}: ClaudeConfigProps) {
  const { register } = useFormContext<WorkflowFormData>();

  return (
    <div className="space-y-4">
      {/* Model Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Model
        </label>
        <select
          {...register(`steps.${stepIndex}.config.model`)}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {MODEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-400">
          Haiku is fastest and cheapest. Sonnet is more capable for complex tasks.
        </p>
      </div>

      {/* Max Tokens */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Max Tokens
        </label>
        <input
          type="number"
          {...register(`steps.${stepIndex}.config.max_tokens`, {
            valueAsNumber: true,
            min: 1,
            max: 4096,
          })}
          placeholder="500"
          min={1}
          max={4096}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-slate-400">
          Maximum length of Claude's response (1-4096). Higher = longer responses but more cost.
        </p>
      </div>

      {/* Prompt */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Prompt <span className="text-red-400">*</span>
        </label>
        <textarea
          {...register(`steps.${stepIndex}.config.prompt`, { required: true })}
          rows={5}
          placeholder="Summarize the following article in 2-3 sentences:

Title: {{trigger.output.title}}
Content: {{trigger.output.content}}"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y font-mono"
        />
        <p className="mt-1 text-xs text-slate-400">
          Use {'{{variables}}'} to include data from triggers or previous steps.
        </p>
      </div>

      {/* Advanced Settings (collapsible) */}
      <details className="group">
        <summary className="cursor-pointer text-sm text-slate-400 hover:text-slate-300">
          Advanced Settings
        </summary>
        <div className="mt-3 space-y-4 pl-2 border-l-2 border-slate-700">
          {/* API Key Secret */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              API Key Secret Name
            </label>
            <input
              type="text"
              {...register(`steps.${stepIndex}.config.api_key_secret`)}
              placeholder="anthropic_api_key"
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-slate-400">
              Name of the secret containing your Anthropic API key (default: anthropic_api_key)
            </p>
          </div>

          {/* Truncate Input */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Truncate Input (chars)
            </label>
            <input
              type="number"
              {...register(`steps.${stepIndex}.config.truncate_input`, {
                valueAsNumber: true,
                min: 100,
                max: 100000,
              })}
              placeholder="4000"
              min={100}
              max={100000}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-slate-400">
              Max characters for the interpolated prompt (default: 4000). Prevents runaway costs.
            </p>
          </div>
        </div>
      </details>

      {/* Variable Helper */}
      <VariableHelper triggerType={triggerType} previousSteps={previousSteps} />
    </div>
  );
}

export default ClaudeConfig;
