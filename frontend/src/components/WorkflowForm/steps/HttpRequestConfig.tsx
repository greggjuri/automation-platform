/**
 * Configuration form for HTTP Request steps.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData, TriggerType, StepType } from '../../../types';
import { KeyValueEditor } from '../KeyValueEditor';
import { VariableHelper } from '../VariableHelper';

interface PreviousStep {
  name: string;
  type: StepType;
}

interface HttpRequestConfigProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Current trigger type */
  triggerType: TriggerType;
  /** Previous steps with name and type */
  previousSteps: PreviousStep[];
}

/**
 * Form fields for configuring an HTTP request step.
 */
export function HttpRequestConfig({
  stepIndex,
  triggerType,
  previousSteps,
}: HttpRequestConfigProps) {
  const { register, watch, setValue } = useFormContext<WorkflowFormData>();

  const method = watch(`steps.${stepIndex}.config.method`) as string;
  const headers = watch(`steps.${stepIndex}.config.headers`) as Record<string, string> || {};

  const showBody = method === 'POST' || method === 'PUT';

  return (
    <div className="space-y-4">
      {/* Method */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Method
        </label>
        <select
          {...register(`steps.${stepIndex}.config.method`)}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
        </select>
      </div>

      {/* URL */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          URL <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          {...register(`steps.${stepIndex}.config.url`, { required: true })}
          placeholder="https://api.example.com/endpoint"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-slate-400">
          Supports variables like {'{{trigger.body.url}}'}
        </p>
      </div>

      {/* Headers */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1">
          Headers
        </label>
        <KeyValueEditor
          value={headers}
          onChange={(newHeaders) =>
            setValue(`steps.${stepIndex}.config.headers`, newHeaders)
          }
          keyPlaceholder="Header name"
          valuePlaceholder="Header value"
          addLabel="Add header"
        />
      </div>

      {/* Body (for POST/PUT) */}
      {showBody && (
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Body
          </label>
          <textarea
            {...register(`steps.${stepIndex}.config.body`)}
            rows={4}
            placeholder='{"key": "value"} or use {{variables}}'
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
          />
        </div>
      )}

      {/* Variable Helper */}
      <VariableHelper triggerType={triggerType} previousSteps={previousSteps} />
    </div>
  );
}

export default HttpRequestConfig;
