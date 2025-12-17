/**
 * Single step editor component.
 *
 * Renders step name, type selector, and type-specific config.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData, StepType } from '../../types';
import {
  HttpRequestConfig,
  TransformConfig,
  LogConfig,
  NotifyConfig,
} from './steps';

interface StepEditorProps {
  /** Index of this step in the steps array */
  stepIndex: number;
  /** Total number of steps (for move buttons) */
  totalSteps: number;
  /** Names of previous steps (for variable helper) */
  previousStepNames: string[];
  /** Callback to move step up */
  onMoveUp: () => void;
  /** Callback to move step down */
  onMoveDown: () => void;
  /** Callback to delete step */
  onDelete: () => void;
}

const STEP_TYPE_LABELS: Record<StepType, string> = {
  http_request: 'HTTP Request',
  transform: 'Transform',
  log: 'Log',
  notify: 'Notify',
};

/**
 * Editor for a single workflow step.
 */
export function StepEditor({
  stepIndex,
  totalSteps,
  previousStepNames,
  onMoveUp,
  onMoveDown,
  onDelete,
}: StepEditorProps) {
  const { register, watch } = useFormContext<WorkflowFormData>();

  const stepType = watch(`steps.${stepIndex}.type`) as StepType;

  const renderConfig = () => {
    const props = { stepIndex, previousStepNames };

    switch (stepType) {
      case 'http_request':
        return <HttpRequestConfig {...props} />;
      case 'transform':
        return <TransformConfig {...props} />;
      case 'log':
        return <LogConfig {...props} />;
      case 'notify':
        return <NotifyConfig {...props} />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
      {/* Step Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-slate-750 border-b border-slate-700">
        {/* Step Number */}
        <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-slate-600 text-xs font-medium text-slate-300">
          {stepIndex + 1}
        </span>

        {/* Step Name */}
        <input
          type="text"
          {...register(`steps.${stepIndex}.name`, { required: true })}
          placeholder="Step name"
          className="flex-1 px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />

        {/* Move Buttons */}
        <div className="flex gap-1">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={stepIndex === 0}
            className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Move up"
          >
            <ChevronUpIcon />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={stepIndex === totalSteps - 1}
            className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Move down"
          >
            <ChevronDownIcon />
          </button>
        </div>

        {/* Delete Button */}
        <button
          type="button"
          onClick={onDelete}
          className="p-1.5 text-slate-400 hover:text-red-400 transition-colors"
          title="Delete step"
        >
          <TrashIcon />
        </button>
      </div>

      {/* Step Config */}
      <div className="p-4 space-y-4">
        {/* Step Type */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Type
          </label>
          <select
            {...register(`steps.${stepIndex}.type`)}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {(Object.entries(STEP_TYPE_LABELS) as [StepType, string][]).map(
              ([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              )
            )}
          </select>
        </div>

        {/* Type-specific Config */}
        {renderConfig()}
      </div>
    </div>
  );
}

function ChevronUpIcon() {
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
        d="M5 15l7-7 7 7"
      />
    </svg>
  );
}

function ChevronDownIcon() {
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
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

function TrashIcon() {
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
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

export default StepEditor;
