/**
 * Configuration form for Transform steps.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData } from '../../../types';
import { VariableHelper } from '../VariableHelper';

interface TransformConfigProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Names of previous steps for variable helper */
  previousStepNames: string[];
}

/**
 * Form fields for configuring a transform step.
 */
export function TransformConfig({
  stepIndex,
  previousStepNames,
}: TransformConfigProps) {
  const { register } = useFormContext<WorkflowFormData>();

  return (
    <div className="space-y-4">
      {/* Template */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Template <span className="text-red-400">*</span>
        </label>
        <textarea
          {...register(`steps.${stepIndex}.config.template`, { required: true })}
          rows={6}
          placeholder={`{
  "result": "{{steps.previous.output}}",
  "timestamp": "{{trigger.body.time}}"
}`}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
        <p className="mt-1 text-xs text-slate-400">
          JSON template with variable interpolation. Use {'{{variable}}'} syntax.
        </p>
      </div>

      {/* Output Key */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Output Key
        </label>
        <input
          type="text"
          {...register(`steps.${stepIndex}.config.output_key`)}
          placeholder="result (optional)"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-slate-400">
          Optional key name for the transformed output. Defaults to step name.
        </p>
      </div>

      {/* Variable Helper */}
      <VariableHelper stepNames={previousStepNames} />
    </div>
  );
}

export default TransformConfig;
