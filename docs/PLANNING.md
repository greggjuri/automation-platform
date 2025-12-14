# PLANNING.md - Automation Platform

> This document defines the project architecture, goals, and constraints.
> Read this at the start of every new conversation.

## Project Vision

Build a personal event-driven automation platform that allows defining workflows with triggers and actions, similar to Zapier or n8n, but self-hosted and tailored to personal/home lab use cases.

**Target user:** Single user (Juri) with potential for multi-user expansion later.

## Goals

1. **Learn AWS serverless patterns** - Event-driven architecture, Step Functions, DynamoDB
2. **Create genuinely useful tool** - Automate tasks across home lab, services, and external APIs
3. **Stay within budget** - ~$20/month AWS spend
4. **Showcase project** - Host publicly at jurigregg.com subdomain

## Non-Goals (for MVP)

- Multi-tenancy / user management
- High availability / multi-region
- Mobile app
- Visual workflow builder (form-based is fine for v0.1)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                   │
│         React + TypeScript on S3/CloudFront                            │
│         automations.jurigregg.com                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                   │
│                    HTTP API with Lambda integration                     │
│  /workflows, /executions, /webhook/{id}                                │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌─────────────────┐           ┌─────────────────┐
          │  API Lambda     │           │ Webhook Lambda  │
          │  (CRUD ops)     │           │ (receives hooks)│
          └────────┬────────┘           └────────┬────────┘
                   │                             │
                   └──────────────┬──────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │       SQS Queue         │
                    │   (execution-queue)     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Execution Starter     │
                    │   Lambda (from SQS)     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Step Functions       │
                    │  (Express Workflow)     │
                    └────────────┬────────────┘
                                 │
         ┌───────────┬───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │  HTTP   │ │ Notify  │ │Transform│ │Database │ │ Custom  │
    │ Request │ │ Action  │ │ Action  │ │ Action  │ │ Lambda  │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         TRIGGERS                                        │
│  EventBridge (cron) │ API Gateway (webhook) │ Poller Lambda (RSS/HTTP) │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA STORES                                      │
│  DynamoDB: workflows, executions, poll_state                           │
│  SSM Parameter Store: secrets, config                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Models

### Workflow

```python
{
    "workflow_id": "wf_abc123",          # PK
    "name": "RSS to Discord",
    "description": "Post new RSS items to Discord",
    "enabled": True,
    "trigger": {
        "type": "poll",                   # webhook | cron | poll | manual
        "config": {
            "url": "https://example.com/feed.xml",
            "interval_minutes": 15,
            "content_type": "rss"
        }
    },
    "steps": [
        {
            "step_id": "step_1",
            "name": "Format message",
            "type": "transform",
            "config": {
                "template": "New post: {{title}} - {{link}}"
            }
        },
        {
            "step_id": "step_2", 
            "name": "Send to Discord",
            "type": "http_request",
            "config": {
                "method": "POST",
                "url": "{{secrets.discord_webhook}}",
                "headers": {"Content-Type": "application/json"},
                "body": {"content": "{{steps.step_1.output}}"}
            }
        }
    ],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

### Execution

```python
{
    "workflow_id": "wf_abc123",           # PK
    "execution_id": "ex_01HQ...",         # SK (ULID for sortability)
    "status": "success",                  # pending | running | success | failed
    "trigger_data": {                     # What triggered this run
        "type": "poll",
        "items": [{"title": "...", "link": "..."}]
    },
    "steps": [
        {
            "step_id": "step_1",
            "status": "success",
            "started_at": "...",
            "finished_at": "...",
            "duration_ms": 45,
            "input": {...},
            "output": {...}
        },
        {
            "step_id": "step_2",
            "status": "success",
            "started_at": "...",
            "finished_at": "...",
            "duration_ms": 230,
            "input": {...},
            "output": {...}
        }
    ],
    "started_at": "2025-01-15T10:45:00Z",
    "finished_at": "2025-01-15T10:45:01Z",
    "error": None
}
```

### Poll State (for polling triggers)

```python
{
    "workflow_id": "wf_abc123",           # PK
    "last_checked_at": "2025-01-15T10:30:00Z",
    "last_content_hash": "abc123...",     # Detect changes
    "seen_item_ids": ["item1", "item2"],  # For RSS, track seen items
    "last_error": None
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /workflows | List all workflows |
| POST | /workflows | Create workflow |
| GET | /workflows/{id} | Get workflow details |
| PUT | /workflows/{id} | Update workflow |
| DELETE | /workflows/{id} | Delete workflow |
| POST | /workflows/{id}/test | Test-run workflow |
| GET | /workflows/{id}/executions | List executions for workflow |
| GET | /executions/{id} | Get execution details |
| POST | /webhook/{workflow_id} | Receive webhook trigger |

## Trigger Types

### MVP (v0.1)
1. **Manual** - Button in UI triggers workflow
2. **Webhook** - External service POSTs to unique URL
3. **Cron** - EventBridge scheduled rule

### Future (v0.2+)
4. **Poll** - Check URL/RSS on interval for changes
5. **Email** - SES inbound email parsing
6. **S3** - Object created/deleted events

## Action Types

### MVP (v0.1)
1. **HTTP Request** - Call any URL with configurable method/headers/body
2. **Transform** - Template string with variable interpolation
3. **Notify** - Send Discord webhook or email (SES)
4. **Log** - Write to execution log (for debugging)

### Future (v0.2+)
5. **Conditional** - If/else branching
6. **Loop** - For each item in array
7. **Delay** - Wait N seconds
8. **Database** - Query/write to DynamoDB
9. **AI** - Summarize/classify with Claude API
10. **Custom Lambda** - User-provided code

## Variable System

Actions can reference:
- `{{trigger.*}}` - Data from the trigger event
- `{{steps.step_id.*}}` - Output from previous steps
- `{{secrets.name}}` - Values from SSM Parameter Store
- `{{env.name}}` - Environment variables

Example:
```json
{
    "type": "http_request",
    "config": {
        "url": "{{secrets.slack_webhook}}",
        "body": {
            "text": "New item: {{trigger.title}} from {{steps.fetch.source}}"
        }
    }
}
```

## CDK Stack Organization

```
cdk/stacks/
├── shared_stack.py      # IAM roles, Parameter Store paths
├── database_stack.py    # DynamoDB tables
├── api_stack.py         # API Gateway + API Lambdas
├── triggers_stack.py    # EventBridge, SQS, Poller
├── execution_stack.py   # Step Functions + Action Lambdas
└── frontend_stack.py    # S3, CloudFront, Route53
```

**Deploy order:** shared → database → triggers → execution → api → frontend

## Cost Estimates

| Service | Monthly Estimate |
|---------|------------------|
| Lambda | $1-2 (free tier likely) |
| API Gateway | $1 |
| Step Functions | $1-3 |
| DynamoDB | $1-2 (on-demand) |
| EventBridge | $0.50 |
| S3 + CloudFront | $1 |
| SQS | $0.50 |
| **Total** | **$8-15** |

## Development Phases

### Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE
- [x] CDK project setup with all stacks
- [x] DynamoDB tables deployed
- [x] Basic API Lambda with CRUD operations
- [x] Simple React app with workflow list/create

**API Endpoint:** https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com

### Phase 2: Execution Engine (Weeks 3-4) - Backend ✅ COMPLETE
- [x] Step Functions state machine (sequential loop pattern for context accumulation)
- [x] SQS queue for execution requests (with DLQ)
- [x] HTTP Request action Lambda
- [x] Transform action Lambda
- [x] Log action Lambda
- [x] Execution Starter Lambda (SQS consumer)
- [x] API endpoints (POST /execute, GET /executions)
- [x] Shared interpolation utility with filters
- [ ] Execution history UI (frontend)
- [ ] Execution detail view (frontend)

### Phase 3: Triggers (Weeks 5-6)
- [ ] Webhook trigger via API Gateway
- [ ] Cron trigger via EventBridge
- [ ] Manual trigger from UI
- [ ] Notification action (Discord)

### Phase 4: Polish (Weeks 7+)
- [ ] Error handling and retries
- [ ] Execution detail view
- [ ] Secrets management UI
- [ ] Polling trigger
- [ ] Visual workflow builder

## Success Criteria

**MVP is complete when:**
1. Can create a workflow via UI
2. Can trigger via webhook or cron
3. Workflow executes HTTP request and transform actions
4. Can view execution history and logs
5. Deployed and accessible at subdomain
6. Costs under $20/month

## Open Questions

- [ ] Auth strategy for API - API key vs Cognito vs none (single user)?
- [ ] How to handle long-running actions (>5 min Express limit)?
- [ ] Workflow versioning - needed for MVP?
