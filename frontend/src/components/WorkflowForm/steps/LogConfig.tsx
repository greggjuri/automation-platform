/**
 * Configuration form for Log steps.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData } from '../../../types';
import { VariableHelper } from '../VariableHelper';

interface LogConfigProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Names of previous steps for variable helper */
  previousStepNames: string[];
}

/**
 * Form fields for configuring a log step.
 */
export function LogConfig({ stepIndex, previousStepNames }: LogConfigProps) {
  const { register } = useFormContext<WorkflowFormData>();

  return (
    <div className="space-y-4">
      {/* Message */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Message <span className="text-red-400">*</span>
        </label>
        <textarea
          {...register(`steps.${stepIndex}.config.message`, { required: true })}
          rows={3}
          placeholder="Processing completed with result: {{steps.previous.output}}"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
        <p className="mt-1 text-xs text-slate-400">
          Log message with optional variable interpolation.
        </p>
      </div>

      {/* Level */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Level
        </label>
        <select
          {...register(`steps.${stepIndex}.config.level`)}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="info">Info</option>
          <option value="warn">Warning</option>
          <option value="error">Error</option>
        </select>
      </div>

      {/* Variable Helper */}
      <VariableHelper stepNames={previousStepNames} />
    </div>
  );
}

export default LogConfig;
