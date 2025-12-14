# PRP-003: Execution Engine Backend

> **Status:** ✅ Implemented
> **Created:** 2025-12-13
> **Implemented:** 2025-12-14
> **Author:** Claude
> **Priority:** P0 (Critical)

---

## Overview

### Problem Statement
The automation platform can create and store workflow definitions, but there's no way to actually run them. Users need to trigger workflow executions, have each step processed sequentially, and view execution results. Without an execution engine, workflows are just inert data.

### Proposed Solution
Build a complete execution engine consisting of:
1. **SQS Queue** for buffering execution requests with DLQ for failed messages
2. **Execution Starter Lambda** that consumes queue messages and starts Step Functions
3. **Step Functions Express** state machine that orchestrates workflow steps
4. **Action Lambdas** for HTTP Request, Transform, and Log actions
5. **API endpoints** for triggering executions and viewing history
6. **Shared interpolation utility** for variable substitution (`{{trigger.data}}`, `{{steps.step_1.output}}`, etc.)

### Out of Scope
- Frontend UI for executions (PRP-004)
- Webhook trigger endpoint (Phase 3)
- Cron/EventBridge triggers (Phase 3)
- Notify action - Discord/email (Phase 3)
- Advanced retry logic (Phase 4)
- Conditional/Loop actions (Future)

---

## Success Criteria

- [x] SQS execution queue and DLQ deployed via CDK
- [x] Step Functions Express state machine deployed and functional
- [x] Execution Starter Lambda processes SQS messages correctly
- [x] HTTP Request action makes external API calls with variable interpolation
- [x] Transform action interpolates templates and mappings
- [x] Log action writes structured logs to CloudWatch
- [x] `POST /workflows/{id}/execute` queues manual execution
- [x] `GET /workflows/{id}/executions` returns paginated execution list
- [x] `GET /workflows/{workflow_id}/executions/{execution_id}` returns full execution details
- [x] Execution records created in DynamoDB with correct status transitions (pending → running → success/failed)
- [x] Failed steps record error details in execution record
- [x] Unit tests for interpolation utility (39 tests for shared utilities)
- [ ] Integration test: manual trigger → HTTP action → verify execution record (requires deployment)

**Definition of Done:**
- All success criteria met
- Tests written and passing
- `cdk synth` and `cdk deploy` succeed
- Manual test via curl shows complete execution flow
- TASK.md updated

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Execution data model, Variable System section, Architecture diagram
- `docs/DECISIONS.md` - ADR-003 (Step Functions Express), ADR-008 (aws-xray-sdk dependency)

### Related Code
- `lambdas/api/handler.py` - Powertools patterns to follow
- `lambdas/api/repository.py` - DynamoDB access patterns
- `cdk/stacks/api_stack.py` - Lambda + API Gateway patterns
- `cdk/stacks/database_stack.py` - Executions table already exists

### Dependencies
- **Requires:** PRP-001 (DynamoDB tables), PRP-002 (API Lambda exists)
- **Blocks:** PRP-004 (Frontend executions view), Phase 3 triggers

### Assumptions
1. Workflows are already validated when saved - execution doesn't re-validate schema
2. Most executions complete in under 5 minutes (Express workflow limit)
3. Single-user MVP means no concurrent execution limits needed
4. Secrets are stored in SSM Parameter Store at `/automation/{env}/secrets/{name}`

---

## Technical Specification

### Data Models

```python
# Execution record (matches PLANNING.md)
class Execution(BaseModel):
    workflow_id: str           # PK
    execution_id: str          # SK (ULID format: ex_01HQ...)
    status: Literal["pending", "running", "success", "failed"]
    trigger_type: str          # manual | webhook | cron | poll
    trigger_data: dict         # Data from trigger event
    steps: list[StepResult]    # Results for each step
    started_at: str | None     # ISO timestamp
    finished_at: str | None    # ISO timestamp
    error: str | None          # Error message if failed
    ttl: int                   # Unix timestamp for DynamoDB TTL (90 days)

class StepResult(BaseModel):
    step_id: str
    status: Literal["pending", "running", "success", "failed", "skipped"]
    started_at: str | None
    finished_at: str | None
    duration_ms: int | None
    input: dict               # What was passed to the action
    output: dict | None       # Action result
    error: str | None         # Error if step failed

# SQS Message format
class ExecutionRequest(BaseModel):
    workflow_id: str
    trigger_type: str
    trigger_data: dict

# Action Lambda standardized I/O
class ActionInput(BaseModel):
    step: dict                 # Step definition from workflow
    context: dict              # {trigger: {...}, steps: {...}, secrets: {...}}

class ActionOutput(BaseModel):
    success: bool
    output: dict | None
    error: str | None
    duration_ms: int
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /workflows/{id}/execute | Queue a manual execution |
| GET | /workflows/{id}/executions | List executions for workflow |
| GET | /workflows/{workflow_id}/executions/{execution_id} | Get execution details |

### Architecture Diagram

```
                    ┌─────────────────────┐
                    │   API Gateway       │
                    │ POST /workflows/    │
                    │      {id}/execute   │
                    └─────────┬───────────┘
                              │
                              ▼
┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  API Lambda  │───▶│    SQS Queue        │───▶│ Execution Starter│
│ (send msg)   │    │ (execution-queue)   │    │    Lambda        │
└──────────────┘    └─────────────────────┘    └────────┬─────────┘
                              │                         │
                              ▼                         │
                    ┌─────────────────────┐             │
                    │   SQS DLQ           │             │
                    │ (after 3 failures)  │             │
                    └─────────────────────┘             │
                                                        │
                              ┌──────────────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │   Step Functions    │
                    │   Express Workflow  │
                    └─────────┬───────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ HTTP Request  │ │  Transform    │ │     Log       │
    │    Lambda     │ │    Lambda     │ │    Lambda     │
    └───────────────┘ └───────────────┘ └───────────────┘
```

### Configuration

```python
# Environment variables for Execution Starter Lambda
WORKFLOWS_TABLE_NAME = "dev-Workflows"
EXECUTIONS_TABLE_NAME = "dev-Executions"
STATE_MACHINE_ARN = "arn:aws:states:us-east-1:xxx:stateMachine:dev-automation-executor"
SSM_SECRETS_PATH = "/automation/dev/secrets"
ENVIRONMENT = "dev"

# Environment variables for Action Lambdas
EXECUTIONS_TABLE_NAME = "dev-Executions"
ENVIRONMENT = "dev"
```

---

## Implementation Steps

### Phase 1: Shared Utilities

#### Step 1.1: Create Interpolation Utility
**Files:** `lambdas/shared/__init__.py`, `lambdas/shared/interpolation.py`
**Description:** Create variable interpolation utility that all action Lambdas will use.

```python
# lambdas/shared/interpolation.py
def interpolate(template: str | dict | list, context: dict) -> str | dict | list:
    """
    Replace {{path.to.value}} with actual values from context.

    Supports:
    - Simple paths: {{trigger.title}}
    - Nested paths: {{steps.step_1.output.data.items[0].name}}
    - Filters: {{trigger.title | upper}}, {{value | default('fallback')}}
    """
```

**Validation:** Unit tests pass for interpolation edge cases

#### Step 1.2: Create Execution ID Generator
**Files:** `lambdas/shared/ids.py`
**Description:** ULID generator for execution IDs (time-sortable)

```python
# lambdas/shared/ids.py
import ulid

def generate_execution_id() -> str:
    """Generate time-sortable execution ID: ex_01HQ..."""
    return f"ex_{ulid.new().str.lower()}"
```

**Validation:** Generated IDs are unique and sortable

### Phase 2: Infrastructure (CDK)

#### Step 2.1: Create Execution Stack Base
**Files:** `cdk/stacks/execution_stack.py`
**Description:** Create the CDK stack with SQS queues

```python
# Create DLQ
execution_dlq = sqs.Queue(
    self, "ExecutionDLQ",
    queue_name=f"{env}-automation-execution-dlq",
    retention_period=Duration.days(14),
)

# Create main queue
execution_queue = sqs.Queue(
    self, "ExecutionQueue",
    queue_name=f"{env}-automation-execution-queue",
    visibility_timeout=Duration.seconds(330),  # > Step Functions 5 min
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=execution_dlq,
    ),
)
```

**Validation:** `cdk synth` succeeds with new stack

#### Step 2.2: Add Action Lambdas to Stack
**Files:** `cdk/stacks/execution_stack.py`
**Description:** Create Lambda functions for each action type

**Validation:** All Lambdas defined with correct permissions

#### Step 2.3: Add Step Functions State Machine
**Files:** `cdk/stacks/execution_stack.py`
**Description:** Create Express workflow state machine

```python
# State machine defined in CDK (not separate ASL file)
state_machine = sfn.StateMachine(
    self, "WorkflowExecutor",
    state_machine_name=f"{env}-automation-executor",
    state_machine_type=sfn.StateMachineType.EXPRESS,
    definition=definition,  # Built using CDK Step Functions constructs
    tracing_enabled=True,
)
```

**Validation:** State machine appears in CDK synth output

#### Step 2.4: Add Execution Starter Lambda
**Files:** `cdk/stacks/execution_stack.py`
**Description:** SQS-triggered Lambda that starts state machine

**Validation:** Lambda has SQS trigger and Step Functions permissions

#### Step 2.5: Wire Up in app.py
**Files:** `cdk/app.py`
**Description:** Add ExecutionStack to CDK app with dependencies

**Validation:** `cdk deploy --all` succeeds

### Phase 3: Action Lambdas

#### Step 3.1: HTTP Request Action
**Files:** `lambdas/action_http_request/handler.py`, `lambdas/action_http_request/requirements.txt`
**Description:** Makes HTTP requests with variable interpolation

```python
# Config schema
{
    "method": "POST",
    "url": "{{secrets.api_url}}/endpoint",
    "headers": {"Authorization": "Bearer {{secrets.api_key}}"},
    "body": {"message": "{{trigger.text}}"},
    "timeout_seconds": 30
}
```

**Validation:** Successfully calls httpbin.org in test

#### Step 3.2: Transform Action
**Files:** `lambdas/action_transform/handler.py`, `lambdas/action_transform/requirements.txt`
**Description:** Template interpolation and object mapping

```python
# Template mode
{"template": "Hello {{trigger.name}}!", "output_key": "greeting"}

# Mapping mode
{"mapping": {"full_name": "{{trigger.first}} {{trigger.last}}"}}
```

**Validation:** Both template and mapping modes work

#### Step 3.3: Log Action
**Files:** `lambdas/action_log/handler.py`, `lambdas/action_log/requirements.txt`
**Description:** Structured logging to CloudWatch

```python
# Config
{"message": "Processing: {{trigger.id}}", "level": "info"}
```

**Validation:** Logs appear in CloudWatch with interpolated values

### Phase 4: Execution Starter Lambda

#### Step 4.1: Create Execution Starter Handler
**Files:** `lambdas/execution_starter/handler.py`, `lambdas/execution_starter/requirements.txt`
**Description:** Consumes SQS, creates execution record, starts Step Functions

```python
def handler(event, context):
    for record in event["Records"]:
        msg = json.loads(record["body"])

        # 1. Fetch workflow from DynamoDB
        workflow = get_workflow(msg["workflow_id"])

        # 2. Generate execution ID and create pending record
        execution_id = generate_execution_id()
        create_execution(workflow_id, execution_id, "pending", msg["trigger_data"])

        # 3. Resolve secrets from SSM
        secrets = resolve_secrets(workflow)

        # 4. Start Step Functions execution
        sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "workflow": workflow,
                "trigger_data": msg["trigger_data"],
                "context": {"trigger": msg["trigger_data"], "steps": {}, "secrets": secrets}
            })
        )
```

**Validation:** Message consumed, execution record created, Step Functions started

#### Step 4.2: Create Execution Repository
**Files:** `lambdas/execution_starter/repository.py`
**Description:** DynamoDB operations for executions

**Validation:** CRUD operations work against Executions table

### Phase 5: API Endpoints

#### Step 5.1: Add Execute Endpoint
**Files:** `lambdas/api/handler.py`
**Description:** `POST /workflows/{id}/execute` sends message to SQS

```python
@app.post("/workflows/<workflow_id>/execute")
def execute_workflow_handler(workflow_id: str) -> dict:
    # Verify workflow exists and is enabled
    # Send SQS message
    # Return {execution_id: "queued", status: "queued"}
```

**Validation:** Curl returns queued status

#### Step 5.2: Add List Executions Endpoint
**Files:** `lambdas/api/handler.py`, `lambdas/api/repository.py`
**Description:** `GET /workflows/{id}/executions` with pagination

```python
@app.get("/workflows/<workflow_id>/executions")
def list_executions_handler(workflow_id: str) -> dict:
    # Query Executions table by workflow_id
    # Support ?limit=20&last_key=... pagination
    # Return {executions: [...], count: N, last_key: ...}
```

**Validation:** Returns paginated execution list

#### Step 5.3: Add Get Execution Endpoint
**Files:** `lambdas/api/handler.py`, `lambdas/api/repository.py`
**Description:** `GET /workflows/{workflow_id}/executions/{execution_id}`

```python
@app.get("/workflows/<workflow_id>/executions/<execution_id>")
def get_execution_handler(workflow_id: str, execution_id: str) -> dict:
    # Get single execution by composite key
    # Return full execution with step details
```

**Validation:** Returns full execution record with step results

### Phase 6: Tests

#### Step 6.1: Unit Tests for Interpolation
**Files:** `lambdas/shared/tests/test_interpolation.py`
**Description:** Comprehensive tests for variable interpolation

Test cases:
- Simple path substitution
- Nested object paths
- Array indexing
- Missing values (error vs empty string)
- Filter: `| upper`, `| lower`, `| default('x')`
- Recursive dict/list interpolation

**Validation:** All tests pass, ≥90% coverage

#### Step 6.2: Unit Tests for Action Lambdas
**Files:** `lambdas/action_*/tests/test_handler.py`
**Description:** Tests for each action Lambda with mocked dependencies

**Validation:** All action tests pass

#### Step 6.3: Integration Test
**Files:** `tests/integration/test_execution_flow.py`
**Description:** End-to-end test: create workflow → execute → verify record

**Validation:** Full flow works against deployed infrastructure

---

## Testing Requirements

### Unit Tests
- [ ] `test_interpolate_simple_path()` - Tests basic `{{trigger.name}}` substitution
- [ ] `test_interpolate_nested_path()` - Tests `{{steps.step_1.output.data}}`
- [ ] `test_interpolate_array_index()` - Tests `{{trigger.items[0].name}}`
- [ ] `test_interpolate_missing_value()` - Tests handling of undefined paths
- [ ] `test_interpolate_filter_upper()` - Tests `{{name | upper}}`
- [ ] `test_interpolate_filter_default()` - Tests `{{name | default('N/A')}}`
- [ ] `test_interpolate_recursive_dict()` - Tests interpolation in nested objects
- [ ] `test_http_request_action_get()` - Tests GET request
- [ ] `test_http_request_action_post()` - Tests POST with body interpolation
- [ ] `test_http_request_action_timeout()` - Tests timeout handling
- [ ] `test_transform_action_template()` - Tests template mode
- [ ] `test_transform_action_mapping()` - Tests mapping mode
- [ ] `test_log_action()` - Tests log output

### Integration Tests
- [ ] `test_execute_workflow_e2e()` - Full execution from API to completion
- [ ] `test_execution_failure_recorded()` - Failed step updates record correctly

### Manual Testing
1. Create a workflow with HTTP + Transform + Log steps via API
2. Execute via `POST /workflows/{id}/execute`
3. Poll `GET /workflows/{id}/executions` until status is "success"
4. Verify `GET /workflows/{id}/executions/{eid}` shows all step results
5. Check CloudWatch for action Lambda logs

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| WorkflowNotFoundError | Execute non-existent workflow | Return 404 |
| WorkflowDisabledError | Execute disabled workflow | Return 400 |
| InterpolationError | Invalid variable path | Fail step, record error |
| HTTPRequestError | External API failure | Fail step, record error + response |
| TimeoutError | Step takes too long | Fail step, record timeout |

### Edge Cases
1. **Empty trigger_data:** Valid - context.trigger is `{}`
2. **Workflow with 0 steps:** Valid - execution completes immediately as success
3. **Very large response:** Truncate HTTP response body to 256KB before storing
4. **Secrets not found:** Fail at execution start, record error
5. **SQS message replay:** Idempotent - check if execution_id already exists

### Rollback Plan
- CDK deployment is atomic per stack
- If ExecutionStack fails, API continues working (just can't execute)
- DLQ captures failed messages for investigation

---

## Performance Considerations

- **Expected latency:** Execution start < 500ms (SQS → Lambda → Step Functions)
- **Expected throughput:** 10-50 executions/minute for MVP (single user)
- **Step Functions Express:** 5 minute max, sufficient for HTTP calls
- **Lambda timeout:** 30s for actions (matches API Gateway limit)
- **DynamoDB:** On-demand, auto-scales

---

## Security Considerations

- [x] Input validation via Pydantic models
- [x] No secrets in code - SSM Parameter Store
- [x] Least privilege IAM (each Lambda gets only needed permissions)
- [ ] HTTP Request action: Consider allowlist of allowed domains (future)
- [ ] Secrets in context are not logged (use Powertools log masking)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +4 functions, ~1000 invocations/month | ~$0.20 |
| Step Functions Express | ~500 executions/month | ~$0.05 |
| SQS | ~1000 messages/month | ~$0.01 |
| CloudWatch Logs | Additional log groups | ~$0.50 |

**Total estimated monthly impact:** ~$1

---

## Open Questions

1. [x] **Variable interpolation errors:** Fail the step (don't silently use empty string) - better for debugging
2. [x] **HTTP response size:** Truncate to 256KB to stay under DynamoDB item limit
3. [x] **Secrets caching:** Cache SSM parameters for 5 minutes in execution starter - reduces SSM API calls and latency across warm Lambda invocations
4. [x] **Step Functions definition:** Use CDK Python constructs (not separate ASL file) - keeps infra together
5. [x] **Execution ID in API:** Require `workflow_id` when fetching execution (Option C from INITIAL) - simplest approach

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | INITIAL doc is detailed, data models defined in PLANNING.md |
| Feasibility | 9 | Step Functions Express fits well, all patterns proven in Phase 1 |
| Completeness | 9 | All open questions resolved, edge cases documented |
| Alignment | 9 | Follows ADR-003 (Step Functions Express), stays within budget |
| **Overall** | **9** | Ready for implementation |

### Remaining Concern
- None - all open questions resolved

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-13 | Claude | Initial draft |
| 2025-12-13 | Juri | Reviewed, resolved secrets caching decision (5 min cache) |
