# PRP-006: Cron Trigger via EventBridge

> **Status:** Ready
> **Created:** 2025-12-16
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement

The automation platform currently supports manual triggers (via UI) and webhook triggers (via external services), but lacks the ability to run workflows on a schedule. Scheduled execution is essential for common automation use cases like:

- Daily reports and notifications
- Periodic health checks and monitoring
- Recurring data sync or cleanup tasks

Without cron triggers, users cannot automate time-based workflows.

### Proposed Solution

Implement EventBridge-based scheduled triggers with the following components:

1. **Cron Handler Lambda**: New Lambda function invoked by EventBridge rules that validates the workflow and queues executions to SQS.

2. **Triggers Stack**: New CDK stack that creates the cron handler Lambda and manages EventBridge rule infrastructure.

3. **EventBridge Rule Management**: Extend the API handler to create/update/delete EventBridge rules when workflows with cron triggers are saved or deleted.

### Out of Scope

- Timezone support in UI (use UTC, user can convert)
- Catch-up for missed schedules (EventBridge doesn't support)
- Sub-minute schedules (EventBridge minimum is 1 minute)
- Visual schedule builder / cron expression helper in UI
- Complex schedule expressions validation beyond EventBridge's native validation

---

## Success Criteria

- [ ] Workflow with `trigger.type: "cron"` creates EventBridge rule on create/update
- [ ] EventBridge rule invokes cron handler Lambda on schedule
- [ ] Cron handler validates workflow exists and is enabled before queueing
- [ ] Disabled workflows are skipped (no execution queued)
- [ ] Execution history shows `trigger_type: "cron"` with scheduled timestamp
- [ ] Deleting workflow removes associated EventBridge rule
- [ ] Updating workflow schedule updates the EventBridge rule
- [ ] Changing workflow from cron to another trigger type removes the rule
- [ ] Unit tests for cron handler (workflow validation, queueing logic)
- [ ] Integration test: schedule fires and execution completes

**Definition of Done:**
- All success criteria met
- Tests written and passing
- Code reviewed
- Documentation updated
- Deployed and tested with real scheduled workflow

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Triggers section: "Cron - EventBridge scheduled rule"
- `docs/DECISIONS.md` - ADR-003: Step Functions Express, ADR-009: Sequential loop pattern

### Related Code
- `lambdas/webhook_receiver/handler.py` - Pattern for trigger Lambda (validates workflow, queues to SQS)
- `lambdas/api/handler.py` - Workflow CRUD operations (where rule management will be added)
- `cdk/stacks/api_stack.py` - API Lambda creation, IAM permissions
- `cdk/stacks/execution_stack.py` - Execution queue, state machine

### Dependencies
- **Requires:**
  - Phase 2 complete (execution engine functional) ✅
  - Webhook trigger functional (pattern to follow) ✅
- **Blocks:**
  - Phase 3 completion
  - Phase 4 polish items

### Assumptions
1. A single cron handler Lambda can handle all scheduled workflows (no per-workflow Lambda)
2. EventBridge rule naming: `{env}-automation-{workflow_id}-schedule`
3. Handler skipping disabled workflows is acceptable (vs disabling rules)
4. EventBridge schedule validation can be delegated to AWS (PutRule will fail for invalid expressions)
5. Workflows only have one active trigger (not multiple)

---

## Technical Specification

### Data Models

No new DynamoDB tables or fields required. Existing workflow model already supports:

```python
{
    "workflow_id": "wf_abc123",
    "name": "Daily Weather",
    "enabled": True,
    "trigger": {
        "type": "cron",  # Already defined in PLANNING.md
        "config": {
            "schedule": "cron(0 13 * * ? *)"  # EventBridge format
        }
    },
    "steps": [...],
    ...
}
```

Trigger data structure for cron executions:

```python
{
    "type": "cron",
    "schedule": "cron(0 13 * * ? *)",       # The schedule expression
    "scheduled_time": "2025-12-17T13:00:00Z", # EventBridge-provided timestamp
    "actual_time": "2025-12-17T13:00:01Z"     # When Lambda actually ran
}
```

### API Changes

No new API endpoints. Existing workflow CRUD endpoints will have side effects:

| Method | Endpoint | Side Effect |
|--------|----------|-------------|
| POST | /workflows | Create EventBridge rule if trigger.type = "cron" |
| PUT | /workflows/{id} | Update/create/delete rule based on trigger changes |
| DELETE | /workflows/{id} | Delete EventBridge rule if it exists |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EventBridge Rules                                │
│   automations-dev-wf_abc123-schedule: cron(0 13 * * ? *)               │
│   automations-dev-wf_def456-schedule: rate(5 minutes)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Invoke on schedule
                                 ▼
                 ┌───────────────────────────────┐
                 │     Cron Handler Lambda        │
                 │  - Extract workflow_id         │
                 │  - Validate workflow exists    │
                 │  - Check enabled=true          │
                 │  - Build trigger_data          │
                 │  - Queue to SQS                │
                 └───────────────┬───────────────┘
                                 │
                                 │ SQS SendMessage
                                 ▼
                   ┌─────────────────────────┐
                   │   Execution Queue       │
                   │   (existing)            │
                   └────────────┬────────────┘
                                │
                                ▼
                       (existing flow)
                   Execution Starter → Step Functions → Actions

┌─────────────────────────────────────────────────────────────────────────┐
│                        API Handler Lambda                                │
│   POST /workflows: create_eventbridge_rule() if trigger.type="cron"    │
│   PUT /workflows: update/delete rule based on trigger changes          │
│   DELETE /workflows: delete_eventbridge_rule()                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### EventBridge Rule Structure

```python
# Rule created by API Lambda
rule_name = f"automations-{env}-{workflow_id}-schedule"
events.put_rule(
    Name=rule_name,
    ScheduleExpression="cron(0 13 * * ? *)",
    State="ENABLED",
    Description=f"Cron trigger for workflow {workflow_id}",
)

# Target (cron handler Lambda)
events.put_targets(
    Rule=rule_name,
    Targets=[{
        "Id": "cron-handler",
        "Arn": cron_handler_lambda_arn,
        "Input": json.dumps({
            "workflow_id": workflow_id,
            "source": "eventbridge-schedule"
        })
    }]
)
```

### Configuration

**Cron Handler Lambda Environment Variables:**
```python
WORKFLOWS_TABLE_NAME = "dev-Workflows"
EXECUTION_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/..."
ENVIRONMENT = "dev"
```

**API Handler Lambda Additional Environment Variables:**
```python
CRON_HANDLER_LAMBDA_ARN = "arn:aws:lambda:us-east-1:...:function:dev-automation-cron-handler"
```

---

## Implementation Steps

### Phase 1: Cron Handler Lambda

#### Step 1.1: Create Cron Handler Lambda
**Files:** `lambdas/cron_handler/handler.py`, `lambdas/cron_handler/requirements.txt`
**Description:** Lambda invoked by EventBridge that validates workflow and queues execution.

```python
# handler.py structure
from aws_lambda_powertools import Logger, Tracer
from datetime import datetime, timezone

logger = Logger(service="cron-handler")
tracer = Tracer(service="cron-handler")

@tracer.capture_method
def get_workflow(workflow_id: str) -> dict | None:
    """Fetch workflow from DynamoDB."""
    ...

@tracer.capture_method
def queue_execution(workflow_id: str, execution_id: str, trigger_data: dict) -> None:
    """Send execution request to SQS."""
    ...

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context) -> dict:
    """Handle EventBridge scheduled invocation.

    Args:
        event: Contains workflow_id, time (scheduled), source
        context: Lambda context

    Returns:
        Status dict with execution_id or skip reason
    """
    workflow_id = event.get("workflow_id")
    scheduled_time = event.get("time")  # EventBridge provides this

    # Validate workflow exists
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.warning("Workflow not found", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_not_found"}

    # Check enabled
    if not workflow.get("enabled", True):
        logger.info("Workflow disabled", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_disabled"}

    # Build trigger data
    trigger_data = {
        "type": "cron",
        "schedule": workflow.get("trigger", {}).get("config", {}).get("schedule", ""),
        "scheduled_time": scheduled_time,
        "actual_time": datetime.now(timezone.utc).isoformat(),
    }

    # Generate execution ID and queue
    execution_id = generate_execution_id()
    queue_execution(workflow_id, execution_id, trigger_data)

    return {"status": "queued", "execution_id": execution_id}
```

**Validation:** Lambda deploys and handles test EventBridge event

#### Step 1.2: Create Unit Tests
**Files:** `lambdas/cron_handler/tests/test_handler.py`
**Description:** Unit tests for cron handler logic.

Test cases:
- Valid workflow queues execution
- Missing workflow returns skipped status
- Disabled workflow returns skipped status
- Trigger data includes schedule and timestamps
- SQS message format is correct

**Validation:** `pytest lambdas/cron_handler/tests -v` passes

### Phase 2: Triggers Stack

#### Step 2.1: Create Triggers Stack
**Files:** `cdk/stacks/triggers_stack.py`
**Description:** CDK stack for cron handler Lambda and related resources.

```python
"""Triggers Stack for Automation Platform.

Creates:
- Cron Handler Lambda (invoked by EventBridge schedules)
"""

class TriggersStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        workflows_table: dynamodb.ITable,
        execution_queue: sqs.IQueue,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment
        self._create_cron_handler(workflows_table, execution_queue)

    def _create_cron_handler(
        self,
        workflows_table: dynamodb.ITable,
        execution_queue: sqs.IQueue,
    ) -> None:
        """Create cron handler Lambda."""
        # Log group, Lambda function, grant DynamoDB read, SQS send
        ...

        # Grant EventBridge permission to invoke
        self.cron_handler.add_permission(
            "EventBridgeInvoke",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # Export ARN for API Lambda to use
        CfnOutput(
            self,
            "CronHandlerArn",
            value=self.cron_handler.function_arn,
            export_name=f"{environment}-automation-cron-handler-arn",
        )
```

**Validation:** `cdk synth` succeeds, stack appears in output

#### Step 2.2: Add Triggers Stack to CDK App
**Files:** `cdk/app.py`
**Description:** Import and instantiate triggers stack.

```python
from stacks.triggers_stack import TriggersStack

# After execution_stack, before api_stack
triggers_stack = TriggersStack(
    app,
    f"{stack_prefix}-triggers",
    workflows_table=database_stack.workflows_table,
    execution_queue=execution_stack.execution_queue,
    environment=environment,
    env=env,
)
```

**Validation:** `cdk synth` shows new stack

### Phase 3: EventBridge Rule Management

#### Step 3.1: Add EventBridge Utilities
**Files:** `lambdas/api/eventbridge.py`
**Description:** Utility functions for EventBridge rule management.

```python
"""EventBridge rule management for cron triggers."""

import boto3
import json
import os

events_client = boto3.client("events")

ENV = os.environ.get("ENVIRONMENT", "dev")
CRON_HANDLER_ARN = os.environ.get("CRON_HANDLER_LAMBDA_ARN", "")

def get_rule_name(workflow_id: str) -> str:
    """Generate rule name from workflow ID."""
    return f"automations-{ENV}-{workflow_id}-schedule"

def create_schedule_rule(workflow_id: str, schedule: str) -> None:
    """Create or update EventBridge rule for cron trigger."""
    rule_name = get_rule_name(workflow_id)

    # Create/update rule
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule,
        State="ENABLED",
        Description=f"Cron trigger for workflow {workflow_id}",
    )

    # Set target to cron handler Lambda
    events_client.put_targets(
        Rule=rule_name,
        Targets=[{
            "Id": "cron-handler",
            "Arn": CRON_HANDLER_ARN,
            "Input": json.dumps({
                "workflow_id": workflow_id,
                "source": "eventbridge-schedule"
            })
        }]
    )

def delete_schedule_rule(workflow_id: str) -> None:
    """Delete EventBridge rule for workflow."""
    rule_name = get_rule_name(workflow_id)

    try:
        # Remove targets first (required before deleting rule)
        events_client.remove_targets(
            Rule=rule_name,
            Ids=["cron-handler"]
        )
        events_client.delete_rule(Name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        pass  # Rule doesn't exist, nothing to delete
```

**Validation:** Unit tests for create/delete functions pass

#### Step 3.2: Integrate EventBridge Management into API Handler
**Files:** `lambdas/api/handler.py`
**Description:** Add rule management to workflow CRUD operations.

Changes to create_workflow_handler:
```python
from eventbridge import create_schedule_rule, delete_schedule_rule

@app.post("/workflows")
def create_workflow_handler() -> dict:
    # ... existing validation and creation ...

    created = create_workflow(item)

    # Create EventBridge rule if cron trigger
    trigger = workflow_data.trigger or {}
    if trigger.get("type") == "cron":
        schedule = trigger.get("config", {}).get("schedule", "")
        if schedule:
            create_schedule_rule(workflow_id, schedule)

    return created
```

Changes to update_workflow_handler:
```python
@app.put("/workflows/<workflow_id>")
def update_workflow_handler(workflow_id: str) -> dict:
    # ... existing validation ...

    # Get current workflow to check trigger changes
    current = get_workflow(workflow_id)

    # ... existing update ...

    # Handle trigger changes
    new_trigger = update_data.trigger or {}
    old_trigger = current.get("trigger", {}) if current else {}

    old_is_cron = old_trigger.get("type") == "cron"
    new_is_cron = new_trigger.get("type") == "cron"

    if new_is_cron:
        # Create or update rule
        schedule = new_trigger.get("config", {}).get("schedule", "")
        if schedule:
            create_schedule_rule(workflow_id, schedule)
    elif old_is_cron and not new_is_cron:
        # Changed away from cron, delete rule
        delete_schedule_rule(workflow_id)

    return updated
```

Changes to delete_workflow_handler:
```python
@app.delete("/workflows/<workflow_id>")
def delete_workflow_handler(workflow_id: str) -> dict:
    # Get workflow first to check trigger type
    workflow = get_workflow(workflow_id)

    # ... existing deletion ...

    # Clean up EventBridge rule if cron trigger
    if workflow and workflow.get("trigger", {}).get("type") == "cron":
        delete_schedule_rule(workflow_id)

    return {"message": f"Workflow {workflow_id} deleted", "workflow_id": workflow_id}
```

**Validation:** Create/update/delete workflows with cron triggers, verify rules created/removed

#### Step 3.3: Update API Stack with EventBridge Permissions
**Files:** `cdk/stacks/api_stack.py`
**Description:** Grant API Lambda permissions to manage EventBridge rules.

```python
# In _create_lambda(), after existing permissions:

# Grant EventBridge permissions for cron trigger management
self.api_handler.add_to_role_policy(
    iam.PolicyStatement(
        actions=[
            "events:PutRule",
            "events:DeleteRule",
            "events:PutTargets",
            "events:RemoveTargets",
            "events:DescribeRule",
        ],
        resources=[
            f"arn:aws:events:{self.region}:{self.account}:rule/automations-{self.env_name}-*"
        ],
    )
)

# Add cron handler ARN to environment (passed from triggers stack)
if cron_handler_arn:
    env_vars["CRON_HANDLER_LAMBDA_ARN"] = cron_handler_arn
```

**Validation:** `cdk synth` succeeds, IAM policy includes EventBridge permissions

#### Step 3.4: Update CDK App to Pass Cron Handler ARN
**Files:** `cdk/app.py`
**Description:** Pass cron handler ARN from triggers stack to API stack.

```python
# Update api_stack creation
api_stack = ApiStack(
    app,
    f"{stack_prefix}-api",
    workflows_table=database_stack.workflows_table,
    executions_table=database_stack.executions_table,
    execution_queue=execution_stack.execution_queue,
    cron_handler_arn=triggers_stack.cron_handler.function_arn,  # NEW
    environment=environment,
    env=env,
)
```

**Validation:** Deployment succeeds, API can create rules

### Phase 4: Integration Testing

#### Step 4.1: Create Integration Tests
**Files:** `lambdas/cron_handler/tests/test_integration.py`
**Description:** Test full cron trigger flow.

Test flow:
1. Create workflow with cron trigger via API
2. Verify EventBridge rule exists
3. Manually invoke cron handler with test event
4. Verify execution queued
5. Delete workflow
6. Verify rule deleted

**Validation:** Integration test passes

#### Step 4.2: Deploy and Manual Testing
**Files:** None (deployment)
**Description:** Deploy and test with real scheduled workflow.

Steps:
1. `cd cdk && cdk deploy --all`
2. Create workflow with `rate(1 minute)` schedule via API
3. Wait 2 minutes, check execution history
4. Verify execution shows `trigger_type: "cron"`
5. Disable workflow, wait, verify no new executions
6. Delete workflow, verify rule deleted

**Validation:** Scheduled executions appear in history

---

## Testing Requirements

### Unit Tests

#### Cron Handler Tests (`lambdas/cron_handler/tests/test_handler.py`)
- [ ] `test_valid_workflow_queued()` - Enabled workflow queues execution
- [ ] `test_workflow_not_found()` - Missing workflow returns skipped
- [ ] `test_workflow_disabled()` - Disabled workflow returns skipped
- [ ] `test_trigger_data_structure()` - Includes schedule, scheduled_time, actual_time
- [ ] `test_sqs_message_format()` - Message has correct structure
- [ ] `test_execution_id_generated()` - Response includes execution_id

#### EventBridge Utilities Tests (`lambdas/api/tests/test_eventbridge.py`)
- [ ] `test_create_rule()` - Rule created with correct schedule
- [ ] `test_update_rule()` - Existing rule updated (idempotent)
- [ ] `test_delete_rule()` - Rule and targets removed
- [ ] `test_delete_nonexistent_rule()` - No error for missing rule
- [ ] `test_rule_naming()` - Follows naming convention

### Integration Tests
- [ ] `test_workflow_create_creates_rule()` - POST /workflows creates EventBridge rule
- [ ] `test_workflow_update_updates_rule()` - PUT /workflows updates rule
- [ ] `test_workflow_delete_deletes_rule()` - DELETE /workflows removes rule
- [ ] `test_change_trigger_type_removes_rule()` - Changing from cron to webhook removes rule
- [ ] `test_cron_to_execution_flow()` - EventBridge → cron handler → SQS → execution

### Manual Testing
1. Create workflow:
   ```json
   {
     "name": "Test Cron",
     "trigger": {"type": "cron", "config": {"schedule": "rate(1 minute)"}},
     "steps": [{"id": "log1", "name": "Log", "type": "log", "config": {"message": "Cron fired!"}}]
   }
   ```
2. Wait 2-3 minutes
3. Check execution history via API: `GET /workflows/{id}/executions`
4. Verify executions have `trigger_type: "cron"`
5. Delete workflow, verify rule removed: `aws events describe-rule --name automations-dev-{workflow_id}-schedule`

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| InvalidScheduleExpression | Bad cron syntax | Let EventBridge PutRule fail, return 400 to user |
| WorkflowNotFound | Deleted between schedule and execution | Skip with warning log |
| WorkflowDisabled | Disabled between schedule and execution | Skip with info log |
| RuleNotFound (on delete) | Rule already deleted | Ignore, log warning |
| EventBridge service error | AWS issue | Return 500, retry later |

### Edge Cases

1. **Workflow deleted while rule exists**: Delete rule in delete handler
2. **Workflow disabled**: Handler skips execution (rule stays enabled for simplicity)
3. **Invalid schedule expression**: Let EventBridge validate and reject with clear error
4. **Rule name collision**: Use workflow_id (ULID) ensures uniqueness
5. **Concurrent rule updates**: PutRule is idempotent, last write wins
6. **Handler invoked for non-cron workflow**: Check trigger type, skip with warning
7. **Circular dependency (triggers stack needs API ARN)**: Use Fn::ImportValue or separate deployment

### Rollback Plan

1. Delete EventBridge rules manually: `aws events delete-rule --name automations-dev-*`
2. Remove triggers stack from app.py
3. Revert API handler changes
4. Redeploy: `cdk deploy --all`

---

## Performance Considerations

- **Expected latency:** Cron handler <100ms (just DynamoDB read + SQS write)
- **Lambda memory:** 256MB sufficient (same as other handlers)
- **Lambda timeout:** 10 seconds (quick validation and queue)
- **EventBridge limits:** 300 rules per region (sufficient for personal use)
- **Concurrent invocations:** Each workflow triggers independently, SQS handles bursts

---

## Security Considerations

- [x] No secrets in code - Cron handler uses IAM roles
- [x] Least privilege IAM - API Lambda only manages rules matching naming pattern
- [x] Rule naming includes environment prefix - Prevents cross-environment conflicts
- [x] EventBridge invokes via IAM - No exposed endpoints
- [ ] Consider: Rate limiting rule creation (prevent DoS via many cron workflows)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +1 function (cron handler) | ~$0.01 |
| EventBridge | +N rules (N = workflows with cron) | ~$0.00 (rules are free, invocations ~$1/M) |
| SQS | Same queue, +invocations | ~$0.00 |

**Estimated monthly impact:** <$0.05 (assuming 100 cron workflows, each firing hourly = 72K invocations/month)

---

## Open Questions

1. ~~**Should disabling a workflow disable the EventBridge rule, or just skip in the handler?**~~
   - **Decision:** Skip in handler (simpler implementation)
   - **Rationale:** Rule management only on create/delete; Lambda cost negligible (~$0.0000002/invocation); easy to optimize later if needed
   - **Status:** ✅ Resolved

2. ~~**Should we create triggers_stack.py or add cron handler to execution_stack.py?**~~
   - **Decision:** New triggers_stack.py
   - **Rationale:** Cleaner separation, follows PLANNING.md stack organization
   - **Note:** Circular dependency requires solution (see below)
   - **Status:** ✅ Resolved

3. **Should we validate schedule expressions in API before calling EventBridge?**
   - **Recommendation:** Let EventBridge validate (simpler, authoritative)
   - **Trade-off:** Slightly worse error messages
   - **Status:** ✅ Accepted

4. **How to handle existing workflows when deploying cron support?**
   - **Recommendation:** No migration needed - rules only created on workflow save
   - **Trade-off:** Existing cron workflows won't have rules until edited
   - **Status:** ✅ Accepted

### Circular Dependency Solution

The triggers stack exports cron handler ARN, and API stack needs it. Solution:

1. **Deploy order:** triggers_stack before api_stack
2. **Use CDK cross-stack reference:** Pass `triggers_stack.cron_handler.function_arn` directly to ApiStack constructor
3. **CDK handles dependency:** Automatically creates correct deployment order

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined in INITIAL-006, clear success criteria |
| Feasibility | 9 | Follows existing patterns, EventBridge is straightforward |
| Completeness | 9 | All components covered; open questions resolved |
| Alignment | 10 | Matches PLANNING.md Phase 3 triggers, uses existing architecture |
| **Overall** | **9.25** | |

### Remaining Considerations

1. **Circular dependency:** Resolved - CDK handles cross-stack references automatically when passing constructs directly.

2. **Testing scheduled execution:** Hard to test without waiting. Mitigations:
   - Use `rate(1 minute)` for quick manual testing
   - Unit test handler with mock EventBridge event
   - Integration test via direct Lambda invocation

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-16 | Claude | Initial draft from INITIAL-006-cron-trigger.md |
| 2025-12-16 | Claude | Resolved open questions: skip-in-handler for disable, triggers_stack.py for location |
