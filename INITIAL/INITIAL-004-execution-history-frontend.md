# INITIAL: Execution History Frontend (PRP-004)

> **Purpose:** This file captures the feature request for Claude Code to expand into a full PRP.
> **Next step:** Run `/generate-prp INITIAL/INITIAL-004-execution-history-frontend.md` in Claude Code.

## Feature Summary

Build the frontend UI to view workflow execution history and trigger manual runs. This includes an execution list on workflow detail pages, a detailed execution view showing step-by-step results with timing, and a "Run" button to manually trigger workflows.

## User Stories

1. As a user, I want to see a list of past executions when viewing a workflow, so I can monitor activity
2. As a user, I want to click on an execution to see step-by-step details (inputs, outputs, timing), so I can debug issues
3. As a user, I want a "Run" button on workflow pages to manually trigger an execution
4. As a user, I want to see execution status badges (pending, running, success, failed) at a glance
5. As a user, I want to see when executions started and how long they took

## Prerequisites / Blockers

⚠️ **Backend Gap Identified:** Per TASK.md, step results are currently not persisted to DynamoDB (execution `steps: []` is empty). The backend needs to save step results for the detail view to work. Options:

1. **Fix in this PRP:** Include a backend fix to persist step results from Step Functions output
2. **Separate PRP:** Create PRP-004a for backend fix, then PRP-004b for frontend
3. **Proceed with frontend:** Build UI assuming steps data exists, test with mock data

**Recommendation:** Include minimal backend fix in this PRP to persist step results, since the feature is incomplete without it.

## Technical Requirements

### 1. Execution List Component

**Location:** Show on workflow detail page (existing or new route)

**Features:**
- Fetch executions via `GET /workflows/{id}/executions`
- Display: status badge, started_at (relative time), duration, execution_id (truncated)
- Pagination support (load more or infinite scroll)
- Empty state: "No executions yet"
- Loading and error states

**Component structure:**
```tsx
// frontend/src/components/ExecutionList.tsx
interface Execution {
  execution_id: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  started_at: string;
  finished_at?: string;
  error?: string;
}

function ExecutionList({ workflowId }: { workflowId: string }) {
  // React Query to fetch executions
  // Map to ExecutionListItem components
  // Handle pagination
}
```

### 2. Execution Detail View

**Route:** `/workflows/:workflowId/executions/:executionId`

**Features:**
- Fetch execution via `GET /workflows/{workflowId}/executions/{executionId}`
- Header: status badge, workflow name, total duration, timestamps
- Steps timeline: ordered list showing each step with:
  - Step name and type
  - Status (success/failed)
  - Duration
  - Expandable input/output JSON (collapsible, syntax highlighted)
- Error display: if failed, show error message prominently

**Component structure:**
```tsx
// frontend/src/pages/ExecutionDetailPage.tsx
interface ExecutionStep {
  step_id: string;
  name: string;
  type: string;
  status: 'success' | 'failed';
  started_at: string;
  finished_at: string;
  duration_ms: number;
  input: object;
  output: object;
  error?: string;
}

interface ExecutionDetail extends Execution {
  workflow_id: string;
  trigger_data: object;
  steps: ExecutionStep[];
}
```

### 3. Manual Run Button

**Location:** Workflow detail page header (near workflow name/actions)

**Features:**
- "Run" or "Execute" button
- Calls `POST /workflows/{id}/execute`
- Shows loading state while queuing
- On success: show toast/notification, optionally navigate to execution detail or refresh list
- On error: show error toast

**Component:**
```tsx
// frontend/src/components/RunWorkflowButton.tsx
function RunWorkflowButton({ workflowId, disabled }: Props) {
  // useMutation for POST /workflows/{id}/execute
  // Loading spinner in button
  // Success/error toast notifications
}
```

### 4. Routing Updates

Add routes:
```tsx
// frontend/src/App.tsx or routes config
<Route path="/workflows/:workflowId" element={<WorkflowDetailPage />} />
<Route path="/workflows/:workflowId/executions/:executionId" element={<ExecutionDetailPage />} />
```

### 5. API Client Functions

Add to existing API module:
```tsx
// frontend/src/api/executions.ts
export async function listExecutions(workflowId: string, limit?: number, lastKey?: string) {
  // GET /workflows/{workflowId}/executions?limit=X&last_key=Y
}

export async function getExecution(workflowId: string, executionId: string) {
  // GET /workflows/{workflowId}/executions/{executionId}
}

export async function executeWorkflow(workflowId: string, triggerData?: object) {
  // POST /workflows/{workflowId}/execute
}
```

### 6. Backend Fix: Persist Step Results

**Problem:** Execution records have `steps: []` because step results aren't being saved.

**Solution:** Update the execution completion flow to save step results:
- Option A: Have the Execution Starter Lambda update the execution record with Step Functions output after `start_sync_execution` returns
- Option B: Add a final state in Step Functions that writes step results to DynamoDB
- Option C: Have each action Lambda update its step result directly

**Recommendation:** Option A is simplest - the sync execution returns all step outputs in the response, so update the execution record with that data in the Execution Starter Lambda.

## Acceptance Criteria

1. [ ] Execution list displays on workflow detail page
2. [ ] Execution list shows status, time, and duration for each execution
3. [ ] Clicking an execution navigates to detail view
4. [ ] Execution detail shows step timeline with expandable input/output
5. [ ] Failed executions show error message clearly
6. [ ] "Run" button triggers workflow execution
7. [ ] "Run" button shows loading state and success/error feedback
8. [ ] Execution list supports pagination
9. [ ] All new components have loading and error states
10. [ ] Backend persists step results to execution record (fix for `steps: []`)

## UI/UX Guidelines

- **Status badges:** 
  - pending: gray/neutral
  - running: blue/pulsing
  - success: green
  - failed: red
- **Timestamps:** Show relative time ("2 minutes ago") with full timestamp on hover
- **Duration:** Show in human-readable format (e.g., "1.2s", "45ms")
- **JSON display:** Use monospace font, syntax highlighting, collapsible sections
- **Keep it simple:** Form-based MVP per ADR-007, no visual timeline needed yet

## Files to Create/Modify

### New Files
```
frontend/src/pages/WorkflowDetailPage.tsx    # Or extend existing
frontend/src/pages/ExecutionDetailPage.tsx
frontend/src/components/ExecutionList.tsx
frontend/src/components/ExecutionListItem.tsx
frontend/src/components/ExecutionStepCard.tsx
frontend/src/components/RunWorkflowButton.tsx
frontend/src/components/StatusBadge.tsx
frontend/src/components/JsonViewer.tsx       # Collapsible JSON display
frontend/src/api/executions.ts               # API functions
frontend/src/hooks/useExecutions.ts          # React Query hooks
```

### Modified Files
```
frontend/src/App.tsx                         # Add routes
frontend/src/api/index.ts                    # Export new API functions
lambdas/execution_starter/handler.py         # Persist step results (backend fix)
```

## Dependencies

- Existing: React Query, React Router, Tailwind CSS
- Consider adding: `date-fns` for relative time formatting, or use built-in Intl.RelativeTimeFormat
- Consider adding: `react-json-view` or similar for JSON display (or build simple custom component)

## Open Questions for PRP

1. **Workflow detail page:** Does it exist yet, or do we need to create it from scratch?
2. **Auto-refresh:** Should execution list auto-refresh while an execution is running?
3. **JSON viewer:** Build custom or use library like `react-json-view`?
4. **Step results backend fix:** Confirm Option A (update in Execution Starter) is acceptable approach
5. **Toast notifications:** Add a toast library (react-hot-toast) or use simple inline messages?

## Context References

- **PLANNING.md:** Execution data model (lines 131-166), Frontend architecture
- **DECISIONS.md:** ADR-005 (React + TypeScript), ADR-007 (Form-based MVP)
- **TASK.md:** Phase 2 remaining items, noted `steps: []` gap
- **Existing code:** `frontend/src/` for current React patterns, `lambdas/api/handler.py` for API endpoints

## Out of Scope (for this PRP)

- Visual workflow builder/timeline
- Real-time execution updates (WebSocket)
- Filtering/searching executions
- Execution retry functionality
- Workflow enable/disable toggle (Phase 4)
