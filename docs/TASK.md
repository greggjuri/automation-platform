# TASK.md - Current Work

> This document tracks active tasks, their status, and blockers.
> Check this before starting any work. Add new tasks as needed.

## Active Tasks

| Task | Status | Assignee | Started | Notes |
|------|--------|----------|---------|-------|
| Create project scaffolding | 🟡 In Progress | Claude Code | 2025-01-XX | Setting up directory structure |

## Backlog (Prioritized)

### Phase 1: Foundation
- [ ] Initialize CDK project with Python
- [ ] Create shared_stack.py (IAM roles, SSM paths)
- [ ] Create database_stack.py (DynamoDB tables)
- [ ] Create api_stack.py (API Gateway + Lambda)
- [ ] Implement workflow CRUD in API Lambda
- [ ] Initialize React frontend with Vite + TypeScript
- [ ] Create workflow list page
- [ ] Create workflow create/edit form
- [ ] Deploy and test end-to-end

### Phase 2: Execution Engine
- [ ] Create SQS queue and DLQ
- [ ] Create execution_stack.py (Step Functions)
- [ ] Implement execution starter Lambda
- [ ] Implement HTTP Request action Lambda
- [ ] Implement Transform action Lambda
- [ ] Implement Log action Lambda
- [ ] Add execution history to frontend
- [ ] Add execution detail view

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
| Context engineering setup | 2025-01-XX | CLAUDE.md, PLANNING.md, TASK.md created |

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
