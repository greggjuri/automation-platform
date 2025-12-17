# INITIAL-006: Cron Trigger via EventBridge

## What I Want

Add scheduled (cron) triggers so workflows can run automatically on a schedule using AWS EventBridge. This completes the core trigger types for Phase 3.

## Why

- **Scheduled automations**: Daily reports, periodic health checks, recurring notifications
- **No external dependency**: Unlike webhooks, cron triggers don't need an external service to initiate
- **Common use case**: Most automation platforms support scheduled triggers as a core feature

## User Stories

1. As a user, I want to schedule a workflow to run every morning at 9am
2. As a user, I want to schedule a workflow to run every 5 minutes for monitoring
3. As a user, I want to see cron-triggered executions in my execution history
4. As a user, I want to disable a workflow and have its schedule stop

## Example Use Case: Daily Weather

```json
{
  "name": "Daily Weather Briefing",
  "enabled": true,
  "trigger": {
    "type": "cron",
    "config": {
      "schedule": "cron(0 13 * * ? *)"
    }
  },
  "steps": [
    {
      "id": "fetch_weather",
      "name": "Fetch Weather",
      "type": "http_request",
      "config": {
        "method": "GET",
        "url": "https://wttr.in/NewYork?format=3"
      }
    },
    {
      "id": "format",
      "name": "Format Message",
      "type": "transform",
      "config": {
        "template": "🌤️ Daily Weather: {{steps.fetch_weather.output.body}}"
      }
    },
    {
      "id": "notify",
      "name": "Send to Discord",
      "type": "notify",
      "config": {
        "service": "discord",
        "webhook_url": "{{secrets.discord_webhook}}",
        "message": "{{steps.format.output.result}}"
      }
    }
  ]
}
```

This runs at 9am EST (13:00 UTC) every day.

## Current State

- ✅ Execution engine works (SQS → Step Functions → Actions)
- ✅ Webhook trigger works (external → API Gateway → Lambda → SQS)
- ✅ Notify action works (Discord)
- ✅ API supports workflow CRUD
- ❌ No scheduled trigger capability

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EventBridge Rule                        │
│         "automations-dev-wf_abc123-schedule"                │
│         Schedule: cron(0 13 * * ? *)                        │
└─────────────────────────────┬───────────────────────────────┘
                              │ Invokes on schedule
                              ▼
              ┌───────────────────────────────┐
              │     Cron Handler Lambda       │
              │  - Receives workflow_id       │
              │  - Validates workflow exists  │
              │  - Checks enabled=true        │
              │  - Queues execution to SQS    │
              └───────────────────┬───────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Execution Queue       │
                    │   (existing SQS)        │
                    └─────────────────────────┘
                                  │
                                  ▼
                         (existing flow)
```

### Key Components

#### 1. Cron Handler Lambda

New Lambda that EventBridge invokes on schedule:

```python
def handler(event, context):
    workflow_id = event["workflow_id"]
    
    # Get workflow from DynamoDB
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.warning(f"Workflow {workflow_id} not found, skipping")
        return {"status": "skipped", "reason": "workflow_not_found"}
    
    if not workflow.get("enabled", True):
        logger.info(f"Workflow {workflow_id} disabled, skipping")
        return {"status": "skipped", "reason": "workflow_disabled"}
    
    # Build trigger data
    trigger_data = {
        "type": "cron",
        "schedule": workflow["trigger"]["config"]["schedule"],
        "scheduled_time": event.get("time"),  # EventBridge provides this
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Queue execution
    execution_id = f"ex_{ulid()}"
    sqs.send_message(...)
    
    return {"status": "queued", "execution_id": execution_id}
```

#### 2. EventBridge Rule Management

Rules are created/updated/deleted when workflows are created/updated/deleted.

**Option A: API Lambda manages rules** (recommended)
- On workflow create/update with cron trigger → create/update EventBridge rule
- On workflow delete → delete EventBridge rule
- On workflow disable → disable rule (or delete)

**Option B: Separate sync process**
- Periodic Lambda scans workflows, syncs rules
- More complex, eventual consistency

**Recommendation:** Option A - immediate, simpler.

#### 3. Rule Naming Convention

```
{app_name}-{env}-{workflow_id}-schedule
Example: automations-dev-wf_abc123-schedule
```

#### 4. IAM Permissions

API Lambda needs:
- `events:PutRule`
- `events:DeleteRule`
- `events:PutTargets`
- `events:RemoveTargets`

Cron Handler Lambda needs:
- `dynamodb:GetItem` (workflows table)
- `sqs:SendMessage` (execution queue)

EventBridge needs:
- `lambda:InvokeFunction` (cron handler)

### Schedule Format

Use EventBridge schedule expressions:
- `rate(5 minutes)` - every 5 minutes
- `rate(1 hour)` - every hour
- `rate(1 day)` - daily
- `cron(0 13 * * ? *)` - daily at 1pm UTC
- `cron(0/15 * * * ? *)` - every 15 minutes

AWS cron format: `cron(minutes hours day-of-month month day-of-week year)`

### Trigger Data for Cron

```python
{
    "type": "cron",
    "schedule": "cron(0 13 * * ? *)",
    "scheduled_time": "2025-12-17T13:00:00Z",  # When EventBridge scheduled it
    "actual_time": "2025-12-17T13:00:01Z"      # When Lambda ran
}
```

## Files to Create/Modify

### New Files
- `lambdas/cron_handler/handler.py`
- `lambdas/cron_handler/requirements.txt`
- `lambdas/cron_handler/tests/test_handler.py`

### Modify
- `cdk/stacks/triggers_stack.py` - Create new stack for cron handler Lambda
- `cdk/stacks/api_stack.py` - Add EventBridge rule management to workflow CRUD
- `cdk/app.py` - Add triggers_stack to deployment
- `lambdas/api_handler/handler.py` - Add rule create/update/delete on workflow CRUD

## Edge Cases

1. **Workflow deleted while rule exists**: Delete rule on workflow delete
2. **Workflow disabled**: Could disable rule or just skip in cron_handler (latter is simpler)
3. **Invalid schedule expression**: Validate in API before creating rule
4. **Rule already exists**: Use PutRule (idempotent - updates if exists)
5. **Concurrent executions**: Each schedule tick queues independently, SQS handles it

## Out of Scope

- Timezone support in UI (use UTC, document conversion)
- Catch-up for missed schedules (EventBridge doesn't support)
- Sub-minute schedules (EventBridge minimum is 1 minute)
- Visual schedule builder in UI (user enters cron expression directly)

## Success Criteria

1. Workflow with cron trigger creates EventBridge rule on save
2. EventBridge fires on schedule and invokes cron handler
3. Cron handler validates workflow and queues execution
4. Execution shows `trigger_type: "cron"` in history
5. Disabling workflow stops executions (either via rule disable or handler skip)
6. Deleting workflow removes EventBridge rule
7. Daily weather workflow runs and posts to Discord

## Questions for Claude

1. Should disabling a workflow disable the EventBridge rule, or just skip in the handler?
   - Disable rule: Cleaner, no Lambda invocations when disabled
   - Skip in handler: Simpler, rule management only on create/delete
   
2. Should we create triggers_stack.py or add to execution_stack.py?
   - Separate stack: Cleaner separation, but adds deployment complexity
   - execution_stack: Co-located with execution infrastructure

3. Validate schedule expression in API or let EventBridge reject invalid ones?
