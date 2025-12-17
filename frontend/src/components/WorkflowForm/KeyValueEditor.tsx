/**
 * Reusable key-value pair editor component.
 *
 * Used for HTTP headers and similar key-value data structures.
 */

interface KeyValuePair {
  key: string;
  value: string;
}

interface KeyValueEditorProps {
  /** Current key-value pairs */
  value: Record<string, string>;
  /** Callback when pairs change */
  onChange: (value: Record<string, string>) => void;
  /** Placeholder for key input */
  keyPlaceholder?: string;
  /** Placeholder for value input */
  valuePlaceholder?: string;
  /** Label for the add button */
  addLabel?: string;
}

/**
 * Editor for key-value pairs with add/remove functionality.
 */
export function KeyValueEditor({
  value,
  onChange,
  keyPlaceholder = 'Key',
  valuePlaceholder = 'Value',
  addLabel = 'Add',
}: KeyValueEditorProps) {
  // Convert Record to array for easier manipulation
  const pairs: KeyValuePair[] = Object.entries(value || {}).map(([k, v]) => ({
    key: k,
    value: v,
  }));

  const handleAdd = () => {
    onChange({ ...value, '': '' });
  };

  const handleRemove = (keyToRemove: string) => {
    const newValue = { ...value };
    delete newValue[keyToRemove];
    onChange(newValue);
  };

  const handleKeyChange = (oldKey: string, newKey: string) => {
    const entries = Object.entries(value);
    const newValue: Record<string, string> = {};

    for (const [k, v] of entries) {
      if (k === oldKey) {
        newValue[newKey] = v;
      } else {
        newValue[k] = v;
      }
    }

    onChange(newValue);
  };

  const handleValueChange = (key: string, newVal: string) => {
    onChange({ ...value, [key]: newVal });
  };

  return (
    <div className="space-y-2">
      {pairs.map((pair, index) => (
        <div key={index} className="flex gap-2">
          <input
            type="text"
            value={pair.key}
            onChange={(e) => handleKeyChange(pair.key, e.target.value)}
            placeholder={keyPlaceholder}
            className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <input
            type="text"
            value={pair.value}
            onChange={(e) => handleValueChange(pair.key, e.target.value)}
            placeholder={valuePlaceholder}
            className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            type="button"
            onClick={() => handleRemove(pair.key)}
            className="px-3 py-2 text-slate-400 hover:text-red-400 transition-colors"
            aria-label="Remove"
          >
            <TrashIcon />
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={handleAdd}
        className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
      >
        <PlusIcon />
        {addLabel}
      </button>
    </div>
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

function PlusIcon() {
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
        d="M12 4v16m8-8H4"
      />
    </svg>
  );
}

export default KeyValueEditor;
