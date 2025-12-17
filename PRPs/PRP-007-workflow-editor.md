# PRP-007: Workflow Create/Edit UI

> **Status:** Ready
> **Created:** 2025-12-16
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement
Workflows can currently only be created and edited via direct API calls. This makes the platform unusable for non-technical users. Per ADR-007, the MVP should have a form-based UI for workflow creation and editing (not a visual node builder).

Users need to:
1. Create new workflows with name, description, trigger, and steps
2. Edit existing workflows
3. Configure different trigger types (manual, webhook, cron)
4. Add/edit/remove steps with type-specific configuration forms
5. Preview the workflow JSON before saving

### Proposed Solution
Build a form-based workflow editor using:
- React Hook Form for form state management and validation
- Type-specific configuration components for each step type
- Step reordering via up/down buttons
- JSON preview panel
- Integration with existing `useCreateWorkflow` and `useUpdateWorkflow` mutation hooks (to be added)

### Out of Scope
- Visual drag-drop workflow builder (per ADR-007)
- Step templates/presets
- Workflow import/export
- Workflow duplication
- Advanced cron builder UI (just text input with examples)

---

## Success Criteria

- [ ] "New Workflow" button on workflows page navigates to create form
- [ ] Create workflow form with name, description, enabled toggle
- [ ] Trigger type selector (Manual, Webhook, Cron) with type-specific config
- [ ] Step list with add/remove/reorder functionality
- [ ] Step type selector (HTTP Request, Transform, Log, Notify)
- [ ] Type-specific configuration forms for all step types
- [ ] Form validation with inline error messages
- [ ] JSON preview panel (collapsible)
- [ ] Save creates workflow via POST /workflows
- [ ] Edit workflow page pre-fills form from existing workflow
- [ ] Update saves changes via PUT /workflows/{id}
- [ ] Success toast and redirect after save
- [ ] "Discard Changes" confirmation when navigating away with unsaved changes

**Definition of Done:**
- All success criteria met
- Code passes ESLint
- Components documented with JSDoc
- Manual testing completed in browser
- Responsive design works on desktop and tablet

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Phase 4 UI polish
- `docs/DECISIONS.md` - ADR-007 (form-based creation for MVP)
- `INITIAL/INITIAL-007-workflow-editor.md` - Detailed requirements

### Related Code
- `frontend/src/hooks/useWorkflows.ts` - Existing query hooks (need mutation hooks)
- `frontend/src/api/client.ts` - Axios client
- `frontend/src/types/workflow.ts` - Workflow, WorkflowStep types
- `lambdas/api/handler.py` - POST/PUT /workflows endpoints
- `lambdas/api/models.py` - WorkflowCreate, WorkflowUpdate Pydantic models

### Dependencies
- **Requires:** PRP-004 Execution History Frontend (complete - provides routing, hooks patterns)
- **Requires:** API endpoints for create/update workflows (already exist)
- **Blocks:** None (enables non-technical users to use the platform)

### Assumptions
1. React Hook Form library already in package.json or can be added
2. Users understand JSON structure basics (for variable syntax like `{{steps.step1.output}}`)
3. Step IDs are auto-generated on frontend before save

---

## Technical Specification

### Data Models (TypeScript)

```typescript
// types/workflow.ts - Add form-specific types

/** Form data for creating/editing a workflow */
export interface WorkflowFormData {
  name: string;
  description: string;
  enabled: boolean;
  trigger: TriggerFormData;
  steps: StepFormData[];
}

/** Trigger configuration in form */
export interface TriggerFormData {
  type: 'manual' | 'webhook' | 'cron';
  config: {
    schedule?: string;  // For cron type
  };
}

/** Step configuration in form */
export interface StepFormData {
  step_id: string;
  name: string;
  type: 'http_request' | 'transform' | 'log' | 'notify';
  config: HttpRequestConfig | TransformConfig | LogConfig | NotifyConfig;
}

/** HTTP Request step config */
export interface HttpRequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  body?: string;
}

/** Transform step config */
export interface TransformConfig {
  template: string;
  output_key?: string;
}

/** Log step config */
export interface LogConfig {
  message: string;
  level: 'info' | 'warn' | 'error';
}

/** Notify step config */
export interface NotifyConfig {
  channel: 'discord';
  webhook_url: string;
  message: string;
  embed?: boolean;
}
```

### API Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /workflows/{id} | Load workflow for edit |
| POST | /workflows | Create new workflow |
| PUT | /workflows/{id} | Update existing workflow |

### Component Architecture

```
frontend/src/
├── components/
│   └── WorkflowForm/
│       ├── WorkflowForm.tsx          # Main form container
│       ├── WorkflowMetadata.tsx      # Name, description, enabled fields
│       ├── TriggerConfig.tsx         # Trigger type selector + config
│       ├── StepList.tsx              # Step list with add/remove/reorder
│       ├── StepEditor.tsx            # Single step editor wrapper
│       ├── steps/
│       │   ├── HttpRequestConfig.tsx # HTTP request form fields
│       │   ├── TransformConfig.tsx   # Transform form fields
│       │   ├── LogConfig.tsx         # Log form fields
│       │   └── NotifyConfig.tsx      # Notify form fields
│       ├── KeyValueEditor.tsx        # Reusable headers editor
│       ├── VariableHelper.tsx        # Available variables hint
│       └── JsonPreview.tsx           # Collapsible JSON preview
├── pages/
│   ├── WorkflowCreatePage.tsx        # /workflows/new route
│   └── WorkflowEditPage.tsx          # /workflows/:id/edit route
└── hooks/
    └── useWorkflowMutations.ts       # Create/update mutation hooks
```

### Routes (add to App.tsx)

| Path | Component | Description |
|------|-----------|-------------|
| `/workflows/new` | WorkflowCreatePage | Create new workflow |
| `/workflows/:id/edit` | WorkflowEditPage | Edit existing workflow |

---

## Implementation Steps

### Phase 1: Foundation (API Hooks & Types)

#### Step 1.1: Add Form Types
**Files:** `frontend/src/types/workflow.ts`
**Description:** Add WorkflowFormData, StepFormData, and step-specific config interfaces

**Validation:** TypeScript compiles without errors

#### Step 1.2: Create Mutation Hooks
**Files:** `frontend/src/hooks/useWorkflowMutations.ts`
**Description:** Add useCreateWorkflow and useUpdateWorkflow mutation hooks

```typescript
export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowFormData) =>
      apiClient.post('/workflows', data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
    },
  });
}

export function useUpdateWorkflow(workflowId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<WorkflowFormData>) =>
      apiClient.put(`/workflows/${workflowId}`, data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(workflowId) });
    },
  });
}
```

**Validation:** Hooks can be imported without errors

#### Step 1.3: Install React Hook Form (if needed)
**Files:** `frontend/package.json`
**Description:** Add react-hook-form dependency

```bash
cd frontend && npm install react-hook-form
```

**Validation:** `npm run build` passes

### Phase 2: Reusable Form Components

#### Step 2.1: KeyValueEditor Component
**Files:** `frontend/src/components/WorkflowForm/KeyValueEditor.tsx`
**Description:** Reusable key-value pair editor for HTTP headers

Features:
- Add new key-value pair
- Remove existing pair
- Edit key and value
- Accepts onChange callback

**Validation:** Component renders and handles add/remove correctly

#### Step 2.2: VariableHelper Component
**Files:** `frontend/src/components/WorkflowForm/VariableHelper.tsx`
**Description:** Tooltip/panel showing available template variables

Shows:
- `{{trigger.body}}` - Webhook payload
- `{{trigger.headers}}` - Webhook headers
- `{{steps.step_name.output}}` - Previous step output
- `{{secrets.name}}` - SSM parameter reference

**Validation:** Component displays variable list

#### Step 2.3: JsonPreview Component
**Files:** `frontend/src/components/WorkflowForm/JsonPreview.tsx`
**Description:** Collapsible panel showing JSON representation

Features:
- Collapse/expand toggle
- Formatted JSON with syntax highlighting (or monospace)
- Updates in real-time as form changes

**Validation:** JSON matches form state

### Phase 3: Step Configuration Components

#### Step 3.1: HttpRequestConfig Component
**Files:** `frontend/src/components/WorkflowForm/steps/HttpRequestConfig.tsx`
**Description:** Form fields for HTTP request step

Fields:
- Method dropdown (GET, POST, PUT, DELETE)
- URL input (required)
- Headers (KeyValueEditor)
- Body textarea (shown for POST/PUT)

**Validation:** All fields render and update form state

#### Step 3.2: TransformConfig Component
**Files:** `frontend/src/components/WorkflowForm/steps/TransformConfig.tsx`
**Description:** Form fields for transform step

Fields:
- Template textarea (required)
- Output key input (optional)

**Validation:** Fields render correctly

#### Step 3.3: LogConfig Component
**Files:** `frontend/src/components/WorkflowForm/steps/LogConfig.tsx`
**Description:** Form fields for log step

Fields:
- Message textarea (required)
- Level dropdown (info, warn, error)

**Validation:** Fields render correctly

#### Step 3.4: NotifyConfig Component
**Files:** `frontend/src/components/WorkflowForm/steps/NotifyConfig.tsx`
**Description:** Form fields for notify step

Fields:
- Channel dropdown (Discord only for now)
- Webhook URL input (or secret reference)
- Message textarea
- Embed toggle checkbox

**Validation:** Fields render correctly

### Phase 4: Core Form Components

#### Step 4.1: StepEditor Component
**Files:** `frontend/src/components/WorkflowForm/StepEditor.tsx`
**Description:** Single step editor with type selector

Features:
- Step name input
- Type dropdown selector
- Renders appropriate config component based on type
- Delete step button
- Move up/down buttons

**Validation:** Type change swaps config component

#### Step 4.2: StepList Component
**Files:** `frontend/src/components/WorkflowForm/StepList.tsx`
**Description:** List of all steps with add button

Features:
- Renders StepEditor for each step
- "Add Step" button at bottom
- Generates step_id on add
- Handles reordering
- Shows step number

**Validation:** Can add/remove/reorder steps

#### Step 4.3: TriggerConfig Component
**Files:** `frontend/src/components/WorkflowForm/TriggerConfig.tsx`
**Description:** Trigger type selector and configuration

Features:
- Type selector (Manual, Webhook, Cron)
- Manual: No additional config
- Webhook: Shows webhook URL (read-only, after save)
- Cron: Schedule expression input with examples

**Validation:** Type change shows/hides config fields

#### Step 4.4: WorkflowMetadata Component
**Files:** `frontend/src/components/WorkflowForm/WorkflowMetadata.tsx`
**Description:** Name, description, enabled fields

Fields:
- Name input (required, 1-100 chars)
- Description textarea (optional)
- Enabled toggle (default: true)

**Validation:** Validation errors display correctly

#### Step 4.5: WorkflowForm Container
**Files:** `frontend/src/components/WorkflowForm/WorkflowForm.tsx`
**Description:** Main form component combining all pieces

Features:
- React Hook Form provider
- Combines metadata, trigger, steps, preview
- Save button with loading state
- Cancel button
- Form-level validation
- Unsaved changes warning (useBeforeUnload)

Props:
- `initialData?: WorkflowFormData` - For edit mode
- `onSubmit: (data: WorkflowFormData) => Promise<void>`
- `isLoading: boolean`

**Validation:** Form submits with valid data

### Phase 5: Pages & Routing

#### Step 5.1: WorkflowCreatePage
**Files:** `frontend/src/pages/WorkflowCreatePage.tsx`
**Description:** Page for creating new workflows

Features:
- Renders WorkflowForm with empty initial state
- Uses useCreateWorkflow mutation
- Shows success toast on save
- Redirects to workflow detail on success

**Validation:** Can create workflow through UI

#### Step 5.2: WorkflowEditPage
**Files:** `frontend/src/pages/WorkflowEditPage.tsx`
**Description:** Page for editing existing workflows

Features:
- Loads workflow via useWorkflow hook
- Renders WorkflowForm with loaded data
- Uses useUpdateWorkflow mutation
- Shows loading state while fetching
- Shows success toast on save
- Redirects to workflow detail on success

**Validation:** Can edit workflow through UI

#### Step 5.3: Add Routes to App.tsx
**Files:** `frontend/src/App.tsx`
**Description:** Add routes for create and edit pages

Add routes:
- `/workflows/new` → WorkflowCreatePage
- `/workflows/:id/edit` → WorkflowEditPage

**Validation:** Navigation works correctly

#### Step 5.4: Add "New Workflow" Button
**Files:** `frontend/src/pages/WorkflowsPage.tsx`
**Description:** Add button linking to create page

Add button in header area that navigates to `/workflows/new`

**Validation:** Button visible and navigates correctly

#### Step 5.5: Add "Edit" Button to Detail Page
**Files:** `frontend/src/pages/WorkflowDetailPage.tsx`
**Description:** Add edit button linking to edit page

Add button next to "Run Now" that navigates to `/workflows/{id}/edit`

**Validation:** Button visible and navigates correctly

### Phase 6: Polish

#### Step 6.1: Form Validation
**Files:** Update all form components
**Description:** Add validation rules

Rules:
- Name: required, 1-100 characters
- Cron expression: validate format (basic regex)
- At least one step required
- HTTP URL: required for http_request type
- Step names should be unique within workflow

**Validation:** Invalid data shows error messages

#### Step 6.2: Unsaved Changes Warning
**Files:** `frontend/src/components/WorkflowForm/WorkflowForm.tsx`
**Description:** Warn before navigating away with unsaved changes

Use `useBeforeUnload` and React Router's `useBlocker` or similar

**Validation:** Browser prompts when leaving with changes

#### Step 6.3: Toast Notifications
**Files:** Add toast component or use library
**Description:** Show success/error toasts

Options:
- Use existing UI library if available
- Add react-hot-toast or similar
- Simple custom toast component

**Validation:** Toasts appear on save success/failure

---

## Testing Requirements

### Unit Tests
- [ ] Form validation logic for workflow name
- [ ] Cron expression validation
- [ ] Step ID generation is unique
- [ ] Form data transformation to API format

### Integration Tests
- [ ] WorkflowForm renders all fields
- [ ] Step type change loads correct config component
- [ ] Form submits correct data structure
- [ ] Edit mode pre-fills form correctly

### Manual Testing
1. Navigate to /workflows/new
2. Fill out all fields, add multiple steps
3. Verify JSON preview matches form
4. Save and verify workflow appears in list
5. Click Edit on existing workflow
6. Modify fields and save
7. Verify changes persisted
8. Test validation errors
9. Test unsaved changes warning
10. Test on mobile/tablet viewport

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Network error | API unreachable | Show error toast, keep form data |
| 400 Bad Request | Invalid workflow data | Show validation error from API |
| 404 Not Found | Workflow deleted during edit | Show error, redirect to list |

### Edge Cases
1. **Very long step names:** Truncate in display, allow full input
2. **Many steps (10+):** Form should still work, consider scrolling
3. **Lost network during save:** Show error, allow retry
4. **Concurrent edit:** Last write wins (no conflict detection for MVP)
5. **Empty headers in HTTP step:** Send empty object, not undefined

### Rollback Plan
Frontend is static files - rollback by deploying previous build

---

## Performance Considerations

- **React Hook Form:** Minimal re-renders, only affected fields update
- **JSON Preview:** Memoize JSON.stringify to avoid recalculation
- **Step Config Components:** Lazy load with React.lazy if bundle grows
- **Form State:** Keep in React Hook Form, not redundant state

---

## Security Considerations

- [x] No secrets in frontend code
- [ ] Sanitize any user input before rendering (step names, descriptions)
- [ ] Webhook URL field should not auto-submit/load
- [ ] Consider limiting step count (e.g., max 20) to prevent abuse

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Frontend | New components | $0 (static files) |
| API calls | Additional POST/PUT | Negligible |

**Total estimated monthly impact:** $0

---

## Open Questions

1. [x] **Toast library:** Should we add react-hot-toast or use a simpler custom solution?
   - **Decision:** Use react-hot-toast (~3KB gzipped)

2. [x] **Step limit:** Should we enforce a maximum number of steps?
   - **Decision:** Skip for MVP, add later if needed

3. [x] **Webhook URL display:** Show webhook URL before first save with placeholder, or only after save?
   - **Decision:** Show "Will be generated after saving" message

4. [x] **Cron field name:** Verify frontend `schedule` matches backend expectation
   - **Verified:** Backend uses `trigger.config.schedule` (see `cron_handler/handler.py:144`, `api/eventbridge.py:149`)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | INITIAL-007 provides detailed requirements |
| Feasibility | 9 | Uses standard React patterns, existing API |
| Completeness | 8.5 | Core functionality covered, toast/validation details TBD |
| Alignment | 9.5 | Directly matches ADR-007 form-based approach |
| **Overall** | **9.0** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-16 | Claude | Initial draft |
