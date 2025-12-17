/**
 * Collapsible JSON preview panel.
 *
 * Shows the workflow JSON that will be sent to the API.
 */

import { useState, useMemo } from 'react';
import type { WorkflowFormData } from '../../types';

interface JsonPreviewProps {
  /** Form data to preview */
  data: WorkflowFormData;
}

/**
 * Collapsible panel showing formatted JSON preview.
 */
export function JsonPreview({ data }: JsonPreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const jsonString = useMemo(() => {
    return JSON.stringify(data, null, 2);
  }, [data]);

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-800 hover:bg-slate-750 transition-colors"
      >
        <span className="text-sm font-medium text-slate-300">
          JSON Preview
        </span>
        <ChevronIcon isExpanded={isExpanded} />
      </button>

      {isExpanded && (
        <div className="p-4 bg-slate-900 border-t border-slate-700">
          <pre className="text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
            {jsonString}
          </pre>
        </div>
      )}
    </div>
  );
}

function ChevronIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <svg
      className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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

export default JsonPreview;
