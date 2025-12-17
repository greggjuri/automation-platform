# INITIAL-007: Workflow Create/Edit UI

## Overview

Add form-based UI for creating and editing workflows. Currently workflows can only be managed via API calls. This feature makes the platform usable without technical knowledge.

**Reference:** ADR-007 specifies form-based creation for MVP (not visual node builder).

## User Stories

1. As a user, I can create a new workflow with name, description, and steps
2. As a user, I can configure different trigger types (manual, webhook, cron)
3. As a user, I can add/edit/remove steps with type-specific configuration
4. As a user, I can see a preview of my workflow before saving
5. As a user, I can edit an existing workflow
6. As a user, I can enable/disable a workflow

## Functional Requirements

### Create Workflow Flow

1. Click "New Workflow" button on dashboard
2. Enter workflow metadata:
   - Name (required)
   - Description (optional)
   - Enabled toggle (default: true)
3. Configure trigger:
   - Type selector: Manual | Webhook | Cron
   - **Manual**: No config needed
   - **Webhook**: Display generated webhook URL (read-only, shows after save)
   - **Cron**: Cron expression input with helper examples
4. Add steps (at least one required):
   - "Add Step" button
   - Step type selector: HTTP Request | Transform | Log | Notify
   - Type-specific config form (see below)
   - Drag-to-reorder steps (or up/down buttons for simplicity)
   - Delete step button
5. Preview JSON (collapsible section)
6. Save button → POST to API

### Step Configuration Forms

**HTTP Request:**
- Name (required)
- Method dropdown: GET | POST | PUT | DELETE
- URL input (supports `{{variables}}`)
- Headers: key-value pairs with add/remove
- Body: textarea (for POST/PUT, supports `{{variables}}`)

**Transform:**
- Name (required)
- Template textarea (supports `{{variables}}`)
- Output variable name (optional, defaults to step_id)

**Log:**
- Name (required)
- Message textarea (supports `{{variables}}`)
- Level dropdown: info | warn | error

**Notify:**
- Name (required)
- Channel: Discord (future: email, Slack)
- Webhook URL input (or `{{secrets.name}}` reference)
- Message textarea (supports `{{variables}}`)
- Embed toggle (Discord-specific)

### Edit Workflow Flow

1. Click workflow card → workflow detail page
2. "Edit" button → opens editor with populated form
3. Same UI as create, but pre-filled
4. PUT to API on save

### Validation Rules

- Name: required, 1-100 characters
- Cron expression: validate format (use library or regex)
- At least one step required
- HTTP URL: required for http_request type
- Step names should be unique within workflow

## Technical Implementation

### New Components

```
frontend/src/
├── components/
│   ├── WorkflowForm/
│   │   ├── WorkflowForm.tsx       # Main form container
│   │   ├── TriggerConfig.tsx      # Trigger type selector + config
│   │   ├── StepList.tsx           # List of steps with add/remove
│   │   ├── StepEditor.tsx         # Individual step edit
│   │   ├── HttpRequestConfig.tsx  # HTTP step config
│   │   ├── TransformConfig.tsx    # Transform step config
│   │   ├── LogConfig.tsx          # Log step config
│   │   ├── NotifyConfig.tsx       # Notify step config
│   │   └── JsonPreview.tsx        # Collapsible JSON preview
│   └── common/
│       ├── KeyValueEditor.tsx     # Reusable key-value pair input
│       └── VariableHint.tsx       # Shows available {{variables}}
├── pages/
│   ├── WorkflowCreate.tsx         # New workflow page
│   └── WorkflowEdit.tsx           # Edit workflow page
└── hooks/
    └── useWorkflowForm.ts         # Form state management
```

### State Management

Use React Hook Form or simple useState for form state. Form structure:

```typescript
interface WorkflowFormData {
  name: string;
  description: string;
  enabled: boolean;
  trigger: {
    type: 'manual' | 'webhook' | 'cron';
    config: {
      cron_expression?: string;  // for cron type
    };
  };
  steps: StepFormData[];
}

interface StepFormData {
  step_id: string;  // auto-generated
  name: string;
  type: 'http_request' | 'transform' | 'log' | 'notify';
  config: Record<string, any>;  // type-specific
}
```

### API Integration

- Create: `POST /workflows` with workflow JSON
- Update: `PUT /workflows/{id}` with workflow JSON
- Existing hooks: `useCreateWorkflow`, `useUpdateWorkflow` (may need to verify/add)

### Routing

Add routes:
- `/workflows/new` → WorkflowCreate page
- `/workflows/:id/edit` → WorkflowEdit page

## UI/UX Notes

- Dark theme consistent with existing pages
- Form sections with clear visual separation
- Inline validation with error messages
- "Discard Changes" confirmation when navigating away with unsaved changes
- Loading states during save
- Success toast on save, redirect to workflow detail

## Variable Helper

Show available variables in a helper panel or tooltip:
- `{{trigger.body}}` - webhook payload
- `{{trigger.headers}}` - webhook headers  
- `{{steps.step_name.output}}` - previous step output
- `{{secrets.name}}` - SSM parameter reference

## Out of Scope (for this PRP)

- Visual drag-drop workflow builder
- Step templates/presets
- Workflow import/export
- Workflow duplication
- Advanced cron builder UI (just text input with examples)

## Testing

- Unit tests for form validation logic
- Component tests for step config forms
- Integration test: create workflow → verify in list → edit → verify changes

## Success Criteria

1. Can create a workflow entirely through UI
2. Can edit existing workflow
3. Form validation prevents invalid workflows
4. JSON preview matches final API payload
5. All step types have appropriate config forms
