# Variable Helper

## Overview
Enhance the workflow editor with contextual variable hints that help users understand what variables are available when configuring step actions. Shows trigger-specific fields, previous step outputs, and secrets.

## Requirements

### Variable Categories

**1. Trigger Variables (based on trigger type)**

| Trigger Type | Available Variables |
|--------------|---------------------|
| Manual | `{{trigger.type}}` |
| Webhook | `{{trigger.type}}`, `{{trigger.payload.*}}`, `{{trigger.headers.*}}`, `{{trigger.query.*}}` |
| Cron | `{{trigger.type}}`, `{{trigger.scheduled_time}}` |
| Poll (RSS/Atom) | `{{trigger.type}}`, `{{trigger.content_type}}`, `{{trigger.items}}`, `{{trigger.items[0].title}}`, `{{trigger.items[0].link}}`, `{{trigger.items[0].guid}}`, `{{trigger.items[0].summary}}` |
| Poll (HTTP) | `{{trigger.type}}`, `{{trigger.content_type}}`, `{{trigger.content}}`, `{{trigger.content_hash}}` |

**2. Step Variables (dynamic based on workflow)**
- Show `{{steps.<step_name>.*}}` for each step defined ABOVE the current step
- Example: If step "fetch_data" is step 1, step 2's helper shows `{{steps.fetch_data.output}}`
- Step output structure depends on action type:
  - HTTP Request: `{{steps.<name>.output.status}}`, `{{steps.<name>.output.body}}`, `{{steps.<name>.output.headers}}`
  - Transform: `{{steps.<name>.output}}` (the transformed result)
  - Log: (no meaningful output)
  - Notify: `{{steps.<name>.output.status_code}}`

**3. Secrets**
- Always show `{{secrets.<name>}}` hint
- Optionally: fetch actual secret names from API and list them

### UI Design

**Location:** Inside each step's configuration section, collapsible panel

**Appearance:**
- Collapsed by default with "Available Variables" header + expand icon
- Glass styling consistent with existing UI
- Monospace font for variable syntax
- Click-to-copy functionality on each variable

**Layout:**
```
┌─────────────────────────────────────────────┐
│ ▶ Available Variables                       │
└─────────────────────────────────────────────┘

[Expanded:]
┌─────────────────────────────────────────────┐
│ ▼ Available Variables                       │
├─────────────────────────────────────────────┤
│ Trigger (poll - rss)                        │
│   {{trigger.type}}              [copy]      │
│   {{trigger.items}}             [copy]      │
│   {{trigger.items[0].title}}    [copy]      │
│   {{trigger.items[0].link}}     [copy]      │
│                                             │
│ Previous Steps                              │
│   {{steps.fetch_data.output}}   [copy]      │
│   {{steps.transform.output}}    [copy]      │
│                                             │
│ Secrets                                     │
│   {{secrets.<name>}}            [copy]      │
│   Tip: Create secrets in Settings > Secrets │
└─────────────────────────────────────────────┘
```

### Behavior
- Updates dynamically as user changes trigger type
- Updates step list as user adds/removes/reorders steps
- Shows only steps defined before current step (can't reference future steps)
- Copy button copies full variable syntax including `{{}}`
- Toast notification on copy: "Copied to clipboard"

## Files to Create/Modify

### New Files
- `frontend/src/components/workflow/VariableHelper.tsx` - Main component

### Modified Files
- `frontend/src/components/workflow/StepConfig.tsx` - Add VariableHelper to each step
- `frontend/src/types/workflow.ts` - Add any needed types

## Implementation Notes

- Use React Hook Form's `watch()` to reactively get current trigger type and steps list
- Filter steps array to only include steps with index < current step index
- Use existing toast system for copy confirmation
- Consider using `navigator.clipboard.writeText()` for copy functionality
- Glass panel styling: `bg-white/5 border border-white/10 rounded-lg`

## Out of Scope
- Auto-complete/suggestions while typing in input fields (future enhancement)
- Validation that referenced variables actually exist
- Fetching actual secret names from API (just show pattern)

## Testing
1. Create workflow with each trigger type, verify correct variables shown
2. Add multiple steps, verify step variables update correctly
3. Reorder steps, verify variable list updates
4. Click copy, verify clipboard contains correct syntax
5. Verify collapsed/expanded state works
