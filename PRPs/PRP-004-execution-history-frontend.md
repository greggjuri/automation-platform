# PRP-004: Execution History Frontend

> **Status:** Ready
> **Created:** 2025-12-14
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement
The execution engine backend is complete (PRP-003), but users cannot view execution history or trigger workflows from the UI. The frontend is currently just the Vite starter template with no actual application logic. Users need to be able to:
1. View a list of past executions for each workflow
2. See execution details including step-by-step results
3. Trigger manual workflow executions from the UI

### Proposed Solution
Build the execution history frontend using React + TypeScript with:
- React Router for navigation between workflows and executions
- React Query for data fetching and caching
- Tailwind CSS for styling
- Reusable components following functional component patterns

The UI will extend the existing workflow list to show executions and provide a detail view for individual executions.

### Out of Scope
- Visual workflow builder (form-based is fine per ADR-007)
- Real-time execution updates via WebSocket
- Execution retry/cancel functionality
- Filtering/search for executions (MVP: simple list)

---

## Success Criteria

- [ ] Workflow list page displays all workflows with execution counts
- [ ] Clicking a workflow navigates to workflow detail with execution history
- [ ] Execution list shows status, trigger type, timestamps with pagination
- [ ] Execution detail page shows all step results with inputs/outputs
- [ ] "Run Now" button triggers manual execution via API
- [ ] Loading states and error handling for all API calls
- [ ] Responsive design works on desktop and mobile
- [ ] All TypeScript types properly defined

**Definition of Done:**
- All success criteria met
- Code passes ESLint
- Components are documented with JSDoc comments
- Manual testing completed in browser

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Phase 2 execution history UI, API endpoints
- `docs/DECISIONS.md` - ADR-005 (React + TypeScript), ADR-007 (form-based MVP)

### Related Code
- `lambdas/api/handler.py` - Existing API endpoints for executions
- `lambdas/api/repository.py` - DynamoDB queries for executions
- `frontend/package.json` - Already has React Query, axios, react-router-dom, Tailwind

### Dependencies
- **Requires:** PRP-003 Execution Engine Backend (complete)
- **Requires:** Step results persistence to DynamoDB (TASK.md backlog item - can work without this initially, steps array will be empty)
- **Blocks:** Phase 3 triggers UI (manual trigger button needed)

### Assumptions
1. API endpoint `https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com` is accessible
2. CORS is configured on API Gateway (if not, will need to add)
3. No authentication required for MVP (single user)

---

## Technical Specification

### Data Models (TypeScript)

```typescript
// types/workflow.ts
export interface Workflow {
  workflow_id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: {
    type: 'manual' | 'webhook' | 'cron' | 'poll';
    config: Record<string, unknown>;
  };
  steps: WorkflowStep[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowStep {
  step_id: string;
  name: string;
  type: 'http_request' | 'transform' | 'log';
  config: Record<string, unknown>;
}

// types/execution.ts
export interface Execution {
  workflow_id: string;
  execution_id: string;
  workflow_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  trigger_type: string;
  trigger_data: Record<string, unknown>;
  steps: ExecutionStep[];
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

export interface ExecutionStep {
  step_id: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
}

// types/api.ts
export interface PaginatedResponse<T> {
  items: T[];
  count: number;
  last_key?: string;
}
```

### API Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /workflows | List all workflows |
| GET | /workflows/{id} | Get single workflow |
| GET | /workflows/{id}/executions | List executions (paginated) |
| GET | /workflows/{id}/executions/{exec_id} | Get execution detail |
| POST | /workflows/{id}/execute | Trigger manual execution |

### Component Architecture

```
src/
├── main.tsx                 # App entry point
├── App.tsx                  # Router setup
├── api/
│   └── client.ts            # Axios instance with base URL
├── hooks/
│   ├── useWorkflows.ts      # React Query hooks for workflows
│   └── useExecutions.ts     # React Query hooks for executions
├── types/
│   ├── workflow.ts          # Workflow types
│   ├── execution.ts         # Execution types
│   └── api.ts               # API response types
├── components/
│   ├── layout/
│   │   ├── Header.tsx       # App header with nav
│   │   └── Layout.tsx       # Main layout wrapper
│   ├── workflows/
│   │   ├── WorkflowList.tsx # List of all workflows
│   │   └── WorkflowCard.tsx # Individual workflow card
│   ├── executions/
│   │   ├── ExecutionList.tsx    # List of executions
│   │   ├── ExecutionRow.tsx     # Single execution row
│   │   └── ExecutionDetail.tsx  # Full execution detail
│   └── common/
│       ├── StatusBadge.tsx      # Status indicator
│       ├── LoadingSpinner.tsx   # Loading state
│       └── ErrorMessage.tsx     # Error display
└── pages/
    ├── WorkflowsPage.tsx        # /workflows route
    ├── WorkflowDetailPage.tsx   # /workflows/:id route
    └── ExecutionDetailPage.tsx  # /workflows/:id/executions/:execId route
```

### Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | Redirect to /workflows | |
| `/workflows` | WorkflowsPage | List all workflows |
| `/workflows/:id` | WorkflowDetailPage | Workflow detail + execution list |
| `/workflows/:id/executions/:execId` | ExecutionDetailPage | Full execution detail |

---

## Implementation Steps

### Phase 1: Foundation

#### Step 1.1: API Client Setup
**Files:** `frontend/src/api/client.ts`
**Description:** Configure axios instance with API base URL

```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com',
  headers: { 'Content-Type': 'application/json' },
});
```

**Validation:** Import works without errors

#### Step 1.2: TypeScript Types
**Files:** `frontend/src/types/workflow.ts`, `frontend/src/types/execution.ts`, `frontend/src/types/api.ts`
**Description:** Define all TypeScript interfaces

**Validation:** `npm run build` passes without type errors

#### Step 1.3: React Query Setup
**Files:** `frontend/src/main.tsx`
**Description:** Wrap app with QueryClientProvider

**Validation:** React Query DevTools visible in browser

### Phase 2: Data Hooks

#### Step 2.1: Workflow Hooks
**Files:** `frontend/src/hooks/useWorkflows.ts`
**Description:** Create hooks for listing and fetching workflows

```typescript
export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: () => apiClient.get('/workflows').then(r => r.data),
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: ['workflows', id],
    queryFn: () => apiClient.get(`/workflows/${id}`).then(r => r.data),
    enabled: !!id,
  });
}
```

**Validation:** Hooks return data when called

#### Step 2.2: Execution Hooks
**Files:** `frontend/src/hooks/useExecutions.ts`
**Description:** Create hooks for executions with pagination and mutations

```typescript
export function useExecutions(workflowId: string, limit = 20) { ... }
export function useExecution(workflowId: string, executionId: string) { ... }
export function useExecuteWorkflow() { ... } // mutation
```

**Validation:** All hooks work with API

### Phase 3: Common Components

#### Step 3.1: Layout Components
**Files:** `frontend/src/components/layout/Header.tsx`, `Layout.tsx`
**Description:** App shell with header and main content area

**Validation:** Layout renders correctly

#### Step 3.2: Status Badge
**Files:** `frontend/src/components/common/StatusBadge.tsx`
**Description:** Colored badge showing execution status

```typescript
// success=green, failed=red, running=yellow, pending=gray
```

**Validation:** All statuses display correctly

#### Step 3.3: Loading and Error Components
**Files:** `frontend/src/components/common/LoadingSpinner.tsx`, `ErrorMessage.tsx`
**Description:** Reusable loading and error states

### Phase 4: Workflow Pages

#### Step 4.1: Workflow List Page
**Files:** `frontend/src/pages/WorkflowsPage.tsx`, `frontend/src/components/workflows/WorkflowList.tsx`, `WorkflowCard.tsx`
**Description:** Display all workflows with name, description, enabled status

**Validation:** Workflows load from API and display

#### Step 4.2: Workflow Detail Page
**Files:** `frontend/src/pages/WorkflowDetailPage.tsx`
**Description:** Workflow info + execution list + "Run Now" button

**Validation:** Page shows workflow details and executions

### Phase 5: Execution Components

#### Step 5.1: Execution List
**Files:** `frontend/src/components/executions/ExecutionList.tsx`, `ExecutionRow.tsx`
**Description:** Table/list of executions with status, timestamps, duration

**Validation:** Executions display with proper formatting

#### Step 5.2: Execution Detail Page
**Files:** `frontend/src/pages/ExecutionDetailPage.tsx`, `frontend/src/components/executions/ExecutionDetail.tsx`
**Description:** Full execution view with expandable step details

**Validation:** All execution data displays including step inputs/outputs

### Phase 6: Router and Polish

#### Step 6.1: Router Setup
**Files:** `frontend/src/App.tsx`
**Description:** Configure React Router with all routes

**Validation:** All routes navigate correctly

#### Step 6.2: Run Now Button
**Files:** Update `WorkflowDetailPage.tsx`
**Description:** Button that triggers execution and shows toast/feedback

**Validation:** Clicking button triggers execution via API

#### Step 6.3: Pagination
**Files:** Update `ExecutionList.tsx`
**Description:** Load more / infinite scroll for execution list

**Validation:** Pagination works with API last_key

---

## Testing Requirements

### Unit Tests
- [ ] `StatusBadge` renders correct colors for each status
- [ ] Date formatting utilities work correctly
- [ ] Type guards for API responses

### Integration Tests
- [ ] `useWorkflows` hook fetches and caches data
- [ ] `useExecuteWorkflow` mutation triggers API call
- [ ] Error states display correctly

### E2E Tests (if applicable)
- [ ] User can navigate from workflow list to execution detail
- [ ] User can trigger manual execution and see it in list

### Manual Testing
1. Load workflows page, verify list displays
2. Click workflow, verify execution history loads
3. Click "Run Now", verify execution queued message
4. Refresh and verify new execution appears
5. Click execution, verify step details display
6. Test on mobile viewport

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| Network error | API unreachable | Show error message with retry button |
| 404 | Workflow/execution not found | Show "not found" message, link to list |
| 400 | Invalid request | Show validation error from API |

### Edge Cases
1. **Empty workflow list:** Show "No workflows yet" message with create prompt
2. **Empty execution list:** Show "No executions yet" message with run prompt
3. **Long-running execution:** Show "running" status with started time
4. **Failed execution:** Show error message prominently in red
5. **Empty steps array:** Show "Step details not available" message

### Rollback Plan
Frontend is static files - rollback by deploying previous build or reverting git commit

---

## Performance Considerations

- **Initial load:** Use React Query staleTime to cache workflow list
- **Execution list:** Paginate with limit=20, load more on scroll
- **Step details:** Collapse by default, expand on click (avoid rendering large JSON)
- **Bundle size:** Already using Vite, tree-shaking enabled

---

## Security Considerations

- [x] No secrets in frontend code (API URL is public)
- [x] No authentication for MVP (single user assumption)
- [ ] Sanitize any user-generated content displayed (step outputs could contain anything)
- [ ] Consider rate limiting on "Run Now" button

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| S3 | Static hosting | ~$0.50 |
| CloudFront | CDN | ~$0.50 |
| API Gateway | Additional calls | Negligible |

**Total estimated monthly impact:** ~$1 (minimal, static hosting)

---

## Open Questions

1. [x] Is CORS configured on API Gateway? (Assuming yes for dev)
2. [ ] Should we add auto-refresh for execution list while viewing? (Nice to have)
3. [ ] Should the step results persistence blocker be completed first? (Can work without it, steps will be empty)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined scope from PLANNING.md and existing API |
| Feasibility | 9 | All dependencies in package.json, API exists |
| Completeness | 8 | Core functionality covered, some nice-to-haves deferred |
| Alignment | 9 | Follows ADR-005, ADR-007, project patterns |
| **Overall** | **8.75** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-14 | Claude | Initial draft |
