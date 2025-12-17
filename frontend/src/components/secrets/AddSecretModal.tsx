/**
 * Add secret modal component.
 *
 * Modal form for creating new secrets.
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import type { CreateSecretRequest, SecretType } from '../../types';
import { SECRET_TYPE_INFO } from '../../types';

interface AddSecretModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Callback to close modal */
  onClose: () => void;
  /** Callback when form is submitted */
  onSubmit: (data: CreateSecretRequest) => void;
  /** Whether submission is in progress */
  isSubmitting?: boolean;
}

const SECRET_TYPES: SecretType[] = ['discord_webhook', 'slack_webhook', 'api_key', 'custom'];

/**
 * Modal form for creating a new secret.
 *
 * @param props - Component props
 */
export function AddSecretModal({ isOpen, onClose, onSubmit, isSubmitting }: AddSecretModalProps) {
  const [selectedType, setSelectedType] = useState<SecretType>('discord_webhook');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateSecretRequest>({
    defaultValues: {
      name: '',
      value: '',
      secret_type: 'discord_webhook',
    },
  });

  // Generate default name based on type
  const getDefaultName = (type: SecretType): string => {
    return type === 'custom' ? '' : type;
  };

  const handleTypeChange = (type: SecretType) => {
    setSelectedType(type);
  };

  const handleFormSubmit = (data: CreateSecretRequest) => {
    onSubmit({
      ...data,
      secret_type: selectedType,
    });
  };

  const handleClose = () => {
    reset();
    setSelectedType('discord_webhook');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md bg-slate-800 rounded-lg border border-slate-700 shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white">Add Secret</h2>
            <button
              onClick={handleClose}
              className="p-1 text-slate-400 hover:text-white transition-colors"
            >
              <CloseIcon />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(handleFormSubmit)} className="p-4 space-y-4">
            {/* Secret Type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Secret Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {SECRET_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleTypeChange(type)}
                    className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                      selectedType === type
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    {SECRET_TYPE_INFO[type].label}
                  </button>
                ))}
              </div>
            </div>

            {/* Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1">
                Name
              </label>
              <input
                {...register('name', {
                  required: 'Name is required',
                  pattern: {
                    value: /^[a-z][a-z0-9_]{0,62}$/,
                    message: 'Name must be lowercase letters, numbers, and underscores, starting with a letter',
                  },
                })}
                id="name"
                type="text"
                placeholder={getDefaultName(selectedType) || 'my_secret'}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-400">{errors.name.message}</p>
              )}
            </div>

            {/* Value */}
            <div>
              <label htmlFor="value" className="block text-sm font-medium text-slate-300 mb-1">
                Value
              </label>
              <input
                {...register('value', { required: 'Value is required' })}
                id="value"
                type="password"
                placeholder={SECRET_TYPE_INFO[selectedType].placeholder}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
              {errors.value && (
                <p className="mt-1 text-sm text-red-400">{errors.value.message}</p>
              )}
              <p className="mt-1 text-xs text-slate-500">
                Stored encrypted. Only the last 4 characters will be shown.
              </p>
            </div>

            {/* Usage hint */}
            <div className="p-3 bg-slate-900/50 rounded-md border border-slate-700">
              <p className="text-xs text-slate-400">
                <strong className="text-slate-300">Usage:</strong> Reference this secret in your
                workflows using{' '}
                <code className="px-1 py-0.5 bg-slate-800 rounded text-blue-400">
                  {'{{secrets.'}
                  <span className="text-slate-300">{getDefaultName(selectedType) || 'name'}</span>
                  {'}}'}
                </code>
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? 'Creating...' : 'Create Secret'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

/** Close icon component */
function CloseIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export default AddSecretModal;
