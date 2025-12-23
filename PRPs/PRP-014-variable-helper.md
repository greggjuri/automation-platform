# PRP-014: Variable Helper Enhancement

> **Status:** Complete
> **Created:** 2025-12-23
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
The current VariableHelper component only shows static webhook trigger variables, regardless of the actual trigger type selected. Users configuring poll, cron, or manual triggers see irrelevant variables (like `{{trigger.body}}`) that don't apply to their trigger type. Additionally, step output variables don't include type-specific hints about what data is available (e.g., HTTP requests have `status`, `body`, `headers`).

### Proposed Solution
Enhance the VariableHelper component to:
1. Show trigger-specific variables based on the current trigger type (manual/webhook/cron/poll)
2. Show step output variables with type-aware structure hints
3. Add click-to-copy functionality for easy variable insertion
4. Use glass styling consistent with the rest of the UI

### Out of Scope
- Auto-complete/suggestions while typing in input fields (future enhancement)
- Validation that referenced variables actually exist
- Fetching actual secret names from API (just show pattern)
- Real-time variable preview/evaluation

---

## Success Criteria

- [x] VariableHelper shows correct variables for each trigger type (manual/webhook/cron/poll)
- [x] Step variables update dynamically as steps are added/removed/reordered
- [x] Only steps ABOVE current step are shown (can't reference future steps)
- [x] Click-to-copy works and shows toast confirmation
- [x] Component uses glass styling (`bg-white/5 border-white/10`)
- [x] Collapsed by default, smooth expand/collapse animation

**Definition of Done:**
- All success criteria met
- Manual testing for all trigger types completed
- Code reviewed
- Documentation updated
- Deployed to dev/staging

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Frontend architecture and UI patterns
- `INITIAL/INITIAL-014-variable-helper.md` - Original feature requirements

### Related Code
- `frontend/src/components/WorkflowForm/VariableHelper.tsx` - Current implementation (to be replaced)
- `frontend/src/components/WorkflowForm/StepEditor.tsx` - Passes previousStepNames to VariableHelper
- `frontend/src/components/WorkflowForm/steps/*.tsx` - Step config components that use VariableHelper
- `frontend/src/types/workflow.ts` - Workflow and step type definitions
- `lambdas/execution_starter/handler.py` - Shows actual trigger data structure passed to workflows

### Dependencies
- **Requires:** Existing toast system for copy confirmations
- **Blocks:** None

### Assumptions
1. React Hook Form's `watch()` is available via `useFormContext` in step config components
2. Existing toast system can be imported and used
3. `navigator.clipboard.writeText()` is available in target browsers

---

## Technical Specification

### Variable Definitions by Trigger Type

```typescript
// Trigger-specific variables
const TRIGGER_VARIABLES: Record<TriggerType, VariableInfo[]> = {
  manual: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("manual")' },
  ],
  webhook: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("webhook")' },
    { syntax: '{{trigger.payload}}', description: 'Webhook request body (JSON)' },
    { syntax: '{{trigger.headers}}', description: 'Request headers object' },
    { syntax: '{{trigger.query}}', description: 'Query string parameters' },
  ],
  cron: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("cron")' },
    { syntax: '{{trigger.scheduled_time}}', description: 'Scheduled execution time' },
  ],
  poll: [
    { syntax: '{{trigger.type}}', description: 'Trigger type ("poll")' },
    { syntax: '{{trigger.content_type}}', description: 'Content type (rss/atom/http)' },
    { syntax: '{{trigger.items}}', description: 'Array of feed items (RSS/Atom)' },
    { syntax: '{{trigger.items[0].title}}', description: 'First item title' },
    { syntax: '{{trigger.items[0].link}}', description: 'First item link' },
    { syntax: '{{trigger.items[0].guid}}', description: 'First item GUID' },
    { syntax: '{{trigger.items[0].summary}}', description: 'First item summary' },
    { syntax: '{{trigger.content}}', description: 'Raw content (HTTP poll)' },
    { syntax: '{{trigger.content_hash}}', description: 'Content hash (HTTP poll)' },
  ],
};
```

### Step Output Variables by Step Type

```typescript
// Step output structure by type
const STEP_OUTPUT_HINTS: Record<StepType, string[]> = {
  http_request: ['output.status', 'output.body', 'output.headers'],
  transform: ['output'],
  log: [], // No meaningful output
  notify: ['output.status_code'],
};
```

### Component Interface

```typescript
interface VariableHelperProps {
  /** Current trigger type to show relevant variables */
  triggerType: TriggerType;
  /** Previous steps (name, type, step_id) for step output variables */
  previousSteps: Array<{
    name: string;
    type: StepType;
  }>;
}

interface VariableInfo {
  syntax: string;
  description: string;
}
```

### Architecture

```
StepEditor
  └── StepConfig (HttpRequestConfig, TransformConfig, etc.)
        └── VariableHelper
              ├── TriggerSection (based on triggerType)
              ├── StepsSection (based on previousSteps)
              └── SecretsSection (static pattern)
```

---

## Implementation Steps

### Phase 1: Enhance VariableHelper Component

#### Step 1.1: Update Component Props and Data Structure
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Replace current static variables with dynamic trigger-type-aware data structures

```typescript
interface VariableHelperProps {
  triggerType: TriggerType;
  previousSteps: Array<{ name: string; type: StepType }>;
}
```

**Validation:** TypeScript compiles without errors

#### Step 1.2: Implement Trigger Variables Section
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Create section that shows variables based on `triggerType` prop

**Validation:** Manual test: change trigger type in form, variables update accordingly

#### Step 1.3: Implement Step Variables Section
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Create section showing `{{steps.<name>.output}}` with type-specific hints

```typescript
// For http_request step named "fetch":
// {{steps.fetch.output.status}}
// {{steps.fetch.output.body}}
// {{steps.fetch.output.headers}}

// For transform step named "parse":
// {{steps.parse.output}}
```

**Validation:** Add multiple steps, verify correct outputs shown for each type

#### Step 1.4: Add Click-to-Copy Functionality
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Add copy button next to each variable, show toast on copy

```typescript
const handleCopy = async (text: string) => {
  await navigator.clipboard.writeText(text);
  toast.success('Copied to clipboard');
};
```

**Validation:** Click copy button, verify clipboard contains variable syntax with `{{}}`

#### Step 1.5: Apply Glass Styling
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Replace slate-700 colors with glass styling

```typescript
// Glass panel styling
className="bg-white/5 border border-white/10 rounded-lg"
```

**Validation:** Visual inspection matches rest of UI

### Phase 2: Update Consumers

#### Step 2.1: Update StepEditor to Pass Trigger Type
**Files:** `frontend/src/components/WorkflowForm/StepEditor.tsx`
**Description:** Watch trigger type from form context and pass to step configs

```typescript
const triggerType = watch('trigger.type') as TriggerType;
```

**Validation:** Console.log triggerType changes when user changes trigger

#### Step 2.2: Update Step Config Components
**Files:** `frontend/src/components/WorkflowForm/steps/*.tsx`
**Description:** Pass triggerType and structured previousSteps to VariableHelper

**Validation:** VariableHelper in each step config shows correct context

---

## Testing Requirements

### Manual Testing
1. Create workflow with **manual** trigger - verify only `{{trigger.type}}` shown
2. Create workflow with **webhook** trigger - verify payload/headers/query shown
3. Create workflow with **cron** trigger - verify scheduled_time shown
4. Create workflow with **poll** trigger - verify items array and content variables shown
5. Add 3 steps, check step 3's helper - verify step 1 and 2 outputs shown
6. Reorder steps - verify variable list updates correctly
7. Click copy button - verify clipboard contains `{{...}}` syntax
8. Verify toast appears on copy
9. Verify collapsed by default, smooth expand
10. Verify glass styling matches rest of UI

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Clipboard write fails | Browser permissions | Show error toast, log warning |

### Edge Cases
1. **No previous steps:** Show "No previous steps" message in Steps section
2. **Step with no output (log):** Don't show output variables for log steps
3. **Unknown trigger type:** Fall back to showing just `{{trigger.type}}`

---

## Performance Considerations

- **No API calls:** All data is derived from form state
- **Minimal re-renders:** Only re-render when trigger type or steps change
- **Memoization optional:** Component is small, memoization likely not needed

---

## Security Considerations

- [x] No external data fetched
- [x] No secrets exposed (just showing pattern)
- [x] Clipboard API is browser-standard

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| N/A | Frontend-only change | $0 |

**Total estimated monthly impact:** $0

---

## Open Questions

All questions resolved - requirements are clear from INITIAL spec.

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined in INITIAL |
| Feasibility | 10 | Simple React component enhancement |
| Completeness | 9 | All edge cases covered |
| Alignment | 10 | Directly improves UX for workflow creation |
| **Overall** | **9.5** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-23 | Claude | Initial draft |
| 2025-12-23 | Claude | Implementation complete - all success criteria met |
