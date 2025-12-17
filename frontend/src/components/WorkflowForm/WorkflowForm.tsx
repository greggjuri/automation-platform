/**
 * Main workflow form component.
 *
 * Combines all form sections with React Hook Form provider.
 */

import { useForm, FormProvider } from 'react-hook-form';
import { useEffect } from 'react';
import type { WorkflowFormData } from '../../types';
import { WorkflowMetadata } from './WorkflowMetadata';
import { TriggerConfig } from './TriggerConfig';
import { StepList } from './StepList';
import { JsonPreview } from './JsonPreview';

interface WorkflowFormProps {
  /** Initial form data (for edit mode) */
  initialData?: WorkflowFormData;
  /** Workflow ID (for edit mode - shows webhook URL) */
  workflowId?: string;
  /** API base URL for webhook display */
  apiBaseUrl?: string;
  /** Submit handler */
  onSubmit: (data: WorkflowFormData) => Promise<void>;
  /** Cancel handler */
  onCancel: () => void;
  /** Whether form is submitting */
  isLoading?: boolean;
  /** Submit button text */
  submitLabel?: string;
}

const DEFAULT_FORM_DATA: WorkflowFormData = {
  name: '',
  description: '',
  enabled: true,
  trigger: {
    type: 'manual',
    config: {},
  },
  steps: [],
};

/**
 * Complete workflow create/edit form.
 */
export function WorkflowForm({
  initialData,
  workflowId,
  apiBaseUrl,
  onSubmit,
  onCancel,
  isLoading = false,
  submitLabel = 'Save Workflow',
}: WorkflowFormProps) {
  const methods = useForm<WorkflowFormData>({
    defaultValues: initialData || DEFAULT_FORM_DATA,
  });

  const {
    handleSubmit,
    watch,
    formState: { isDirty },
  } = methods;

  // Watch all form data for JSON preview
  const formData = watch();

  // Warn about unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const handleFormSubmit = async (data: WorkflowFormData) => {
    try {
      await onSubmit(data);
    } catch (error) {
      // Error handling is done in parent component
      console.error('Form submit error:', error);
    }
  };

  const handleCancel = () => {
    if (isDirty) {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave?'
      );
      if (!confirmed) return;
    }
    onCancel();
  };

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-8">
        {/* Metadata Section */}
        <section className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <WorkflowMetadata />
        </section>

        {/* Trigger Section */}
        <section className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <TriggerConfig workflowId={workflowId} apiBaseUrl={apiBaseUrl} />
        </section>

        {/* Steps Section */}
        <section className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <StepList />
        </section>

        {/* JSON Preview */}
        <JsonPreview data={formData} />

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-4">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex items-center px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <LoadingSpinner />
                Saving...
              </>
            ) : (
              submitLabel
            )}
          </button>
        </div>
      </form>
    </FormProvider>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin -ml-1 mr-2 h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default WorkflowForm;
