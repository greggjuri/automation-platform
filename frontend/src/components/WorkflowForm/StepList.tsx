/**
 * Step list component with add/remove/reorder functionality.
 */

import { useFieldArray, useFormContext } from 'react-hook-form';
import type { WorkflowFormData, StepFormData, TriggerType, StepType } from '../../types';
import { StepEditor } from './StepEditor';

interface PreviousStep {
  name: string;
  type: StepType;
}

/**
 * Generate a unique step ID.
 */
function generateStepId(): string {
  return `step_${Math.random().toString(36).substring(2, 10)}`;
}

/**
 * Create default config for a step type.
 */
function getDefaultConfig(
  type: string
): StepFormData['config'] {
  switch (type) {
    case 'http_request':
      return { method: 'GET', url: '', headers: {}, body: '' };
    case 'transform':
      return { template: '', output_key: '' };
    case 'log':
      return { message: '', level: 'info' };
    case 'notify':
      return { channel: 'discord', webhook_url: '', message: '', embed: false };
    default:
      return { method: 'GET', url: '', headers: {}, body: '' };
  }
}

/**
 * List of workflow steps with add/remove/reorder.
 */
export function StepList() {
  const { control, watch } = useFormContext<WorkflowFormData>();

  const { fields, append, remove, move } = useFieldArray({
    control,
    name: 'steps',
  });

  const steps = watch('steps') || [];
  const triggerType = watch('trigger.type') as TriggerType;

  const handleAddStep = () => {
    const newStep: StepFormData = {
      step_id: generateStepId(),
      name: `Step ${fields.length + 1}`,
      type: 'http_request',
      config: getDefaultConfig('http_request'),
    };
    append(newStep);
  };

  const handleMoveUp = (index: number) => {
    if (index > 0) {
      move(index, index - 1);
    }
  };

  const handleMoveDown = (index: number) => {
    if (index < fields.length - 1) {
      move(index, index + 1);
    }
  };

  const getPreviousSteps = (currentIndex: number): PreviousStep[] => {
    return steps.slice(0, currentIndex).map((s) => ({
      name: s.name || '',
      type: s.type,
    }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Steps</h3>
        <span className="text-sm text-slate-400">
          {fields.length} step{fields.length !== 1 ? 's' : ''}
        </span>
      </div>

      {fields.length === 0 ? (
        <div className="text-center py-8 bg-slate-800/50 border-2 border-dashed border-slate-700 rounded-lg">
          <p className="text-slate-400 mb-4">No steps yet</p>
          <button
            type="button"
            onClick={handleAddStep}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
          >
            <PlusIcon />
            Add First Step
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {fields.map((field, index) => (
              <StepEditor
                key={field.id}
                stepIndex={index}
                totalSteps={fields.length}
                triggerType={triggerType}
                previousSteps={getPreviousSteps(index)}
                onMoveUp={() => handleMoveUp(index)}
                onMoveDown={() => handleMoveDown(index)}
                onDelete={() => remove(index)}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={handleAddStep}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-600 rounded-lg text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
          >
            <PlusIcon />
            Add Step
          </button>
        </>
      )}
    </div>
  );
}

function PlusIcon() {
  return (
    <svg
      className="w-5 h-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 4v16m8-8H4"
      />
    </svg>
  );
}

export default StepList;
