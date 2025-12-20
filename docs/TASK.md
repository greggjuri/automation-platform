# TASK.md - Current Work

> This document tracks active tasks, their status, and blockers.
> Check this before starting any work. Add new tasks as needed.

## Active Tasks

| Task | Status | Assignee | Started | Notes |
|------|--------|----------|---------|-------|
| _No active tasks_ | | | | |

## Backlog (Prioritized)

### Phase 1: Foundation ✅ COMPLETE
- [x] Initialize CDK project with Python
- [x] Create shared_stack.py (IAM roles, SSM paths)
- [x] Create database_stack.py (DynamoDB tables)
- [x] Create api_stack.py (API Gateway + Lambda)
- [x] Implement workflow CRUD in API Lambda
- [x] Initialize React frontend with Vite + TypeScript
- [x] Deploy and test end-to-end

**API Endpoint:** https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com
**Frontend URL:** https://automations.jurigregg.com

### Phase 2: Execution Engine ✅ COMPLETE
- [x] Create SQS queue and DLQ
- [x] Create execution_stack.py (Step Functions Express)
- [x] Implement execution starter Lambda
- [x] Implement HTTP Request action Lambda
- [x] Implement Transform action Lambda
- [x] Implement Log action Lambda
- [x] Add API endpoints for executions
- [x] Shared interpolation utility with filters
- [x] Save step results to execution record
- [x] Add execution history to frontend
- [x] Add execution detail view

**Known Issues (to address in Phase 4):**
- SSM permissions for secrets (warning in logs when no secrets configured)
- Interpolation error handling for missing variables

### Phase 3: Triggers ✅ COMPLETE
- [x] Implement webhook receiver Lambda
- [x] Add webhook route to API Gateway (POST /webhook/{workflow_id})
- [x] Implement Notify action Lambda (Discord webhook)
- [x] Add Notify action to Step Functions state machine
- [x] Unit tests for webhook receiver (19 tests)
- [x] Unit tests for notify action (15 tests)
- [x] Implement EventBridge cron trigger (PRP-006)
  - [x] Cron handler Lambda
  - [x] Triggers CDK stack
  - [x] EventBridge rule management in API
  - [x] Unit tests (12 tests)
- [x] Deploy and test end-to-end (cron + webhook)
- [x] Add manual trigger button to UI
- [x] Test full workflow: webhook → transform → notify

### Phase 4: Polish
- [x] Workflow create/edit UI (PRP-007)
- [x] Secrets management UI (PRP-009)
- [x] Frontend styling and UX improvements (PRP-010)
  - [x] Glass button component with variants
  - [x] Centralized error handling utility
  - [x] Retry button for failed executions
  - [x] Failed step highlighting
  - [x] Pure black background + silver text theme
- [x] Workflow enable/disable (PRP-011)
- [ ] Authentication with read-only public access (PRP-012)
- [ ] Polling trigger
- [ ] VariableHelper: show trigger-specific fields (webhook: payload/headers, cron: scheduled_time)
- [ ] README.md and architecture docs
- [ ] User guide (plain English, examples)
- [ ] API reference documentation

### Cleanup
- [ ] Delete or .gitignore examples/auth/ files after PRP-012 implementation

## Completed Tasks

| Task | Completed | Notes |
|------|-----------|-------|
| Architecture design | 2025-01-XX | Documented in PLANNING.md |
| Create project scaffolding | 2025-12-12 | Directory structure, initial docs |
| Context engineering setup | 2025-12-12 | Slash commands, PRP template, examples folder |
| PRP-001: Project Foundation | 2025-12-12 | CDK stacks, DynamoDB tables, Lambda dirs, Frontend init |
| PRP-002: API Gateway + Workflow CRUD | 2025-12-12 | HTTP API, Lambda handler with Powertools, full CRUD ops, 19 unit tests |
| **Phase 1: Foundation** | 2025-12-12 | All infrastructure deployed. API: https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com |
| PRP-003: Execution Engine Backend | 2025-12-14 | SQS queues, Step Functions Express, Action Lambdas (HTTP, Transform, Log), Execution Starter, API endpoints, 58 tests |
| PRP-003 Runtime Fixes | 2025-12-14 | Fixed: API routes, shared module bundling, IAM StartSyncExecution, step type path, sequential loop for context accumulation, step failure propagation |
| **Phase 2: Execution Engine Backend** | 2025-12-14 | All backend components complete. Frontend execution views remain. |
| PRP-004: Execution History Frontend | 2025-12-14 | React Query hooks, Workflow list/detail pages, Execution list/detail pages, Run Now button, Status badges |
| Step Results Persistence | 2025-12-14 | Parse SFN output, extract step results with name/type/status/output/error, persist to DynamoDB |
| Frontend Deployment | 2025-12-14 | CDK frontend_stack.py: S3 + CloudFront + Route 53 for automations.jurigregg.com |
| PRP-005: Webhook Trigger + Notify Action | 2025-12-16 | Webhook receiver Lambda, Notify action Lambda (Discord), CDK updates, 34 unit tests |
| PRP-006: Cron Trigger | 2025-12-16 | Cron handler Lambda, triggers_stack.py, EventBridge rule management in API, 12 unit tests |
| PRP-007: Workflow Create/Edit UI | 2025-12-16 | Form-based workflow editor with React Hook Form, step config components, toast notifications |
| PRP-008: Frontend BucketDeployment | 2025-12-17 | Add BucketDeployment to frontend_stack.py for automatic S3 upload and CloudFront invalidation |
| Step Functions step_id fix | 2025-12-17 | Fixed context merge using $.step.step_id instead of $.step.id in UpdateContext state |
| DynamoDB reserved words fix | 2025-12-17 | Alias all attribute names in update_workflow to handle reserved words (trigger, status, etc.) |
| Step context key fix | 2025-12-17 | Use step.name instead of step_id for context keys (e.g., steps.fetch_data.output) |
| Delete workflow UI | 2025-12-17 | Red Delete button with confirmation modal on workflow detail page |
| Frontend display bug fixes | 2025-12-17 | WorkflowCard trigger/steps, ExecutionDetail step status by name, empty trigger message |
| Transform action output_key fix | 2025-12-17 | Handle empty string output_key from frontend with `or "result"` fallback |
| TriggerConfig cron buttons | 2025-12-17 | Use React Hook Form setValue() instead of DOM manipulation for cron example buttons |
| EventBridge InputTransformer | 2025-12-17 | Pass EventBridge $.time to cron handler via InputTransformer for trigger_data.scheduled_time |
| PRP-009: Secrets Management UI | 2025-12-17 | Full-stack secrets CRUD: SSM SecureString storage, API endpoints (GET/POST/DELETE /secrets), SecretsPage, AddSecretModal, DeleteSecretModal, 14 unit tests |
| SSM secrets path alignment | 2025-12-17 | Fixed path mismatch: API was writing to /automations/ but execution_starter reading from /automation/ |
| PRP-010: Frontend Polish | 2025-12-17 | Glass button component, error handler utility, retry button for failed executions, failed step highlighting, pure black theme |
| PRP-011: Workflow Enable/Disable | 2025-12-19 | PATCH /workflows/{id}/enabled endpoint, EventBridge rule enable/disable, ToggleSwitch component, disabled workflow visual feedback, 11 unit tests |

## Blockers

_None currently_

## Notes

### How to Add a Task
When starting work not listed here, add it:
```markdown
| Task description | 🟡 In Progress | Your name | YYYY-MM-DD | Any relevant notes |
```

### Status Legend
- ⬜ Not started
- 🟡 In Progress
- 🟢 Complete
- 🔴 Blocked
- ⏸️ Paused

### Task Sizing
- **Small:** < 2 hours (single Lambda, single component)
- **Medium:** 2-8 hours (full stack feature, CDK stack)
- **Large:** > 8 hours (break into smaller tasks)
