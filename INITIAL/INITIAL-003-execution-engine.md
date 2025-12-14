# INITIAL: Execution Engine Backend

> **Purpose:** This file captures the feature request for Claude Code to expand into a full PRP.
> **Next step:** Run `/generate-prp INITIAL-003-execution-engine.md` in Claude Code.

## Feature Summary

Build the backend execution engine that actually runs workflows. This includes an SQS queue for execution requests, Step Functions Express for orchestration, action Lambdas (HTTP Request, Transform, Log), and API endpoints for triggering executions and viewing history.

## User Stories

1. As a user, I want to trigger a workflow execution via API so that I can test my workflows
2. As a user, I want to see a list of past executions for a workflow so I can monitor activity
3. As a user, I want to see execution details (each step's input/output/timing) so I can debug issues
4. As a system, executions should be queued via SQS so that spikes don't overwhelm the system
5. As a system, failed executions should go to a DLQ so they can be investigated

## Technical Requirements

### 1. SQS Queue Infrastructure

Create execution queue and dead-letter queue:

```python
# In execution_stack.py
execution_dlq = sqs.Queue(
    self, "ExecutionDLQ",
    queue_name="automation-execution-dlq",
    retention_period=Duration.days(14),
)

execution_queue = sqs.Queue(
    self, "ExecutionQueue",
    queue_name="automation-execution-queue",
    visibility_timeout=Duration.seconds(330),  # 5.5 min (longer than Step Function max)
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=execution_dlq,
    ),
)
```

### 2. Step Functions Express State Machine

Create a state machine that:
- Receives workflow definition and trigger data as input
- Iterates through steps array
- Calls appropriate action Lambda for each step type
- Passes step output to next step's context
- Records final execution result

**State Machine Input:**
```json
{
  "execution_id": "ex_01HQ...",
  "workflow_id": "wf_abc123",
  "workflow": { /* full workflow definition */ },
  "trigger_data": { /* data from trigger */ },
  "context": {
    "trigger": { /* alias for trigger_data */ },
    "steps": {},
    "secrets": {}
  }
}
```

**State Machine Structure (ASL conceptual):**
```
StartExecution
  → UpdateExecutionStatus(running)
  → Map over workflow.steps
    → Choice by step.type
      → http_request: InvokeHttpRequestLambda
      → transform: InvokeTransformLambda  
      → log: InvokeLogLambda
    → UpdateStepResult (add to context.steps)
  → UpdateExecutionStatus(success)
  → Catch: UpdateExecutionStatus(failed)
```

### 3. Execution Starter Lambda

**Trigger:** SQS event from execution_queue

**Responsibilities:**
1. Parse SQS message containing `{workflow_id, trigger_data, trigger_type}`
2. Fetch workflow from DynamoDB
3. Generate execution_id (ULID for sortability)
4. Create Execution record in DynamoDB with status="pending"
5. Resolve `{{secrets.*}}` variables from SSM Parameter Store
6. Start Step Functions execution with prepared input
7. Handle errors gracefully (update execution status to "failed")

**Location:** `lambdas/execution_starter/`

### 4. Action Lambdas

Each action Lambda receives standardized input and returns standardized output:

**Input:**
```json
{
  "step": {
    "step_id": "step_1",
    "name": "Fetch data",
    "type": "http_request",
    "config": { /* step-specific config */ }
  },
  "context": {
    "trigger": { /* trigger data */ },
    "steps": {
      "previous_step_id": { "output": { /* ... */ } }
    },
    "secrets": { /* resolved secrets */ }
  }
}
```

**Output:**
```json
{
  "success": true,
  "output": { /* step result */ },
  "error": null,
  "duration_ms": 145
}
```

#### 4a. HTTP Request Action (`lambdas/action_http_request/`)

Config:
```json
{
  "method": "GET|POST|PUT|DELETE|PATCH",
  "url": "https://api.example.com/data",
  "headers": { "Authorization": "Bearer {{secrets.api_key}}" },
  "body": { "message": "{{trigger.text}}" },
  "timeout_seconds": 30
}
```

- Interpolate variables in url, headers, body before request
- Use `requests` library (or `httpx` for async)
- Return response status, headers, body (parsed as JSON if possible)
- Handle timeouts and HTTP errors gracefully

#### 4b. Transform Action (`lambdas/action_transform/`)

Config:
```json
{
  "template": "New item: {{trigger.title}} - {{trigger.link}}",
  "output_key": "message"
}
```

OR for object transformation:
```json
{
  "mapping": {
    "formatted_title": "{{trigger.title | upper}}",
    "source_url": "{{trigger.link}}",
    "fetched_at": "{{steps.step_1.output.timestamp}}"
  }
}
```

- Support simple `{{path.to.value}}` interpolation
- Support basic filters: `| upper`, `| lower`, `| default('fallback')`
- Use Jinja2 or a simple custom parser

#### 4c. Log Action (`lambdas/action_log/`)

Config:
```json
{
  "message": "Processing item: {{trigger.title}}",
  "level": "info"
}
```

- Interpolate variables in message
- Write to CloudWatch Logs with structured format
- Useful for debugging workflows

### 5. API Endpoints

Add to existing API Lambda (`lambdas/api/`):

| Method | Path | Description |
|--------|------|-------------|
| POST | /workflows/{id}/execute | Queue a manual execution |
| GET | /workflows/{id}/executions | List executions for workflow |
| GET | /executions/{id} | Get execution details |

#### POST /workflows/{id}/execute
- Validate workflow exists and is enabled
- Send message to SQS queue: `{workflow_id, trigger_data: {type: "manual"}, trigger_type: "manual"}`
- Return `{execution_id, status: "queued"}`

#### GET /workflows/{id}/executions
- Query DynamoDB Executions table by workflow_id (PK)
- Support pagination via `?limit=20&last_key=...`
- Return list sorted by execution_id descending (newest first)

#### GET /executions/{id}
- Need GSI on execution_id or scan (discuss in PRP)
- Return full execution record including step details

### 6. Variable Interpolation Utility

Create shared utility (`lambdas/shared/interpolation.py`):

```python
def interpolate(template: str | dict, context: dict) -> str | dict:
    """
    Replace {{path.to.value}} with actual values from context.
    
    Context structure:
    {
        "trigger": {...},
        "steps": {"step_id": {"output": {...}}},
        "secrets": {"name": "value"}
    }
    """
```

- Handle nested paths: `{{steps.step_1.output.data.items[0].name}}`
- Handle missing values gracefully (empty string or error?)
- Support in strings and recursively in dicts/lists

### 7. DynamoDB Considerations

**Executions Table Access Patterns:**
- Get executions by workflow: `PK=workflow_id`, query by SK (execution_id)
- Get single execution by execution_id: Need GSI or composite key design

**Option A:** GSI on execution_id (adds cost, simpler queries)
**Option B:** Store workflow_id in execution_id format: `ex_{workflow_id}_{ulid}`
**Option C:** Require workflow_id when fetching execution (client provides both)

Recommend **Option C** for MVP - keeps it simple, client can store both IDs.

## Acceptance Criteria

1. [ ] SQS queue and DLQ deployed via CDK
2. [ ] Step Functions Express state machine deployed
3. [ ] Execution Starter Lambda processes queue messages
4. [ ] HTTP Request action makes external API calls with variable interpolation
5. [ ] Transform action interpolates templates
6. [ ] Log action writes to CloudWatch
7. [ ] POST /workflows/{id}/execute queues execution
8. [ ] GET /workflows/{id}/executions returns paginated list
9. [ ] GET /executions/{id} returns full execution details
10. [ ] Execution records created in DynamoDB with correct status transitions
11. [ ] Failed steps/executions recorded with error details
12. [ ] Unit tests for interpolation utility
13. [ ] Integration test: manual trigger → HTTP action → verify execution record

## Files to Create/Modify

### New Files
```
cdk/stacks/execution_stack.py          # SQS, Step Functions, Action Lambdas
lambdas/execution_starter/handler.py   # SQS consumer
lambdas/execution_starter/requirements.txt
lambdas/action_http_request/handler.py
lambdas/action_http_request/requirements.txt
lambdas/action_transform/handler.py
lambdas/action_transform/requirements.txt
lambdas/action_log/handler.py
lambdas/action_log/requirements.txt
lambdas/shared/interpolation.py        # Variable interpolation utility
tests/unit/test_interpolation.py
tests/unit/test_action_transform.py
tests/integration/test_execution_flow.py
```

### Modified Files
```
cdk/app.py                             # Add ExecutionStack
lambdas/api/handler.py                 # Add execution endpoints
lambdas/api/requirements.txt           # If new deps needed
```

## Dependencies

- `requests` or `httpx` for HTTP action
- `jinja2` for template interpolation (or custom parser)
- `ulid-py` for execution ID generation
- Existing: `aws-lambda-powertools`, `boto3`, `aws-xray-sdk`

## Open Questions for PRP

1. **Variable interpolation errors:** Fail the step or use empty string for missing variables?
2. **HTTP action response size:** Truncate large responses to prevent DynamoDB item size issues?
3. **Secrets caching:** Cache SSM parameters in execution starter or fetch fresh each time?
4. **Step Functions definition:** Define in CDK Python or separate ASL JSON file?
5. **Execution ID in API:** Require `workflow_id` when fetching execution, or add GSI?

## Context References

- **PLANNING.md:** Execution data model, Variable System section, API endpoints
- **DECISIONS.md:** ADR-003 (Step Functions Express), ADR-008 (aws-xray-sdk dependency)
- **Existing code:** `lambdas/api/handler.py` for Powertools patterns, `cdk/stacks/` for CDK patterns

## Out of Scope (for this PRP)

- Frontend UI for executions (PRP-004)
- Webhook trigger (Phase 3)
- Cron trigger (Phase 3)
- Notify action (Phase 3)
- Retry logic and advanced error handling (Phase 4)
- Conditional/Loop actions (Future)
