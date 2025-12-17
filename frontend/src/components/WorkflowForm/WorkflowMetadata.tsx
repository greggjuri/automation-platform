/**
 * Workflow metadata fields component.
 *
 * Name, description, and enabled toggle.
 */

import { useFormContext } from 'react-hook-form';
import type { WorkflowFormData } from '../../types';

/**
 * Form fields for workflow metadata (name, description, enabled).
 */
export function WorkflowMetadata() {
  const {
    register,
    formState: { errors },
  } = useFormContext<WorkflowFormData>();

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Details</h3>

      {/* Name */}
      <div>
        <label
          htmlFor="name"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Name <span className="text-red-400">*</span>
        </label>
        <input
          id="name"
          type="text"
          {...register('name', {
            required: 'Name is required',
            minLength: { value: 1, message: 'Name is required' },
            maxLength: { value: 100, message: 'Name must be under 100 characters' },
          })}
          placeholder="My Workflow"
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {errors.name && (
          <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Description
        </label>
        <textarea
          id="description"
          {...register('description', {
            maxLength: { value: 500, message: 'Description must be under 500 characters' },
          })}
          rows={2}
          placeholder="Describe what this workflow does..."
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
        />
        {errors.description && (
          <p className="mt-1 text-xs text-red-400">{errors.description.message}</p>
        )}
      </div>

      {/* Enabled Toggle */}
      <div className="flex items-center gap-3">
        <input
          id="enabled"
          type="checkbox"
          {...register('enabled')}
          className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-800"
        />
        <label htmlFor="enabled" className="text-sm text-slate-300">
          Enabled
        </label>
        <span className="text-xs text-slate-400">
          (Disabled workflows will not execute)
        </span>
      </div>
    </div>
  );
}

export default WorkflowMetadata;
