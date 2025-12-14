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

### Phase 2: Execution Engine
- [x] Create SQS queue and DLQ
- [x] Create execution_stack.py (Step Functions Express)
- [x] Implement execution starter Lambda
- [x] Implement HTTP Request action Lambda
- [x] Implement Transform action Lambda
- [x] Implement Log action Lambda
- [x] Add API endpoints for executions
- [x] Shared interpolation utility with filters
- [ ] **Save step results to execution record** (steps: [] is empty — step details not persisted to DynamoDB)
- [x] Add execution history to frontend
- [x] Add execution detail view

### Phase 3: Triggers
- [ ] Create triggers_stack.py
- [ ] Implement webhook receiver Lambda
- [ ] Implement EventBridge cron rule creation
- [ ] Add manual trigger button to UI
- [ ] Implement Notify action (Discord webhook)
- [ ] Test full workflow: webhook → transform → notify

### Phase 4: Polish
- [ ] Error handling and retry logic
- [ ] Secrets management UI
- [ ] Workflow enable/disable
- [ ] Polling trigger
- [ ] Frontend styling and UX improvements
- [ ] Documentation and README

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
