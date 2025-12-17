# PRP-005: Webhook Trigger + Notify Action

> **Status:** Implemented (pending deployment)
> **Created:** 2025-12-16
> **Implemented:** 2025-12-16
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement

The automation platform currently supports manual workflow triggering via the UI, but external services (GitHub, Stripe, home automation) cannot trigger workflows automatically. Additionally, workflows have no way to produce visible notifications - the only output is execution logs.

### Proposed Solution

1. **Webhook Receiver Lambda**: New Lambda function handling `POST /webhook/{workflow_id}` that receives external HTTP requests, extracts trigger data, and queues workflow executions.

2. **Notify Action Lambda**: New action Lambda that posts messages to Discord webhooks, enabling workflows to produce visible output.

Together, these enable the first real end-to-end automation: external event → process → notification.

### Out of Scope

- Webhook signature verification (HMAC for GitHub, Stripe) - Phase 4
- Slack/Email notify services - Phase 4
- Retry on Discord failure - Phase 4
- Frontend UI for copying webhook URL (can use API endpoint directly)
- Rate limiting for webhooks (not needed for personal use)

---

## Success Criteria

- [ ] `POST /webhook/{workflow_id}` with JSON body queues execution
- [ ] `POST /webhook/{workflow_id}` with form-urlencoded body queues execution
- [ ] Webhook returns 202 Accepted with execution_id immediately
- [ ] Webhook returns 404 for non-existent workflows
- [ ] Webhook returns 400 for disabled workflows
- [ ] Execution shows `trigger_type: "webhook"` and contains POST body in trigger_data
- [ ] Notify action posts message to Discord channel
- [ ] Notify action truncates messages over 2000 chars
- [ ] Full flow works: `curl webhook → transform → discord message appears`

**Definition of Done:**
- All success criteria met
- Tests written and passing (unit + integration)
- Code reviewed
- Documentation updated
- Deployed and tested with real GitHub webhook

---

## Context

### Related Documentation
- `docs/PLANNING.md` - API endpoints table includes `/webhook/{workflow_id}`, Notify action in MVP
- `docs/DECISIONS.md` - ADR-009 Sequential Step Functions loop pattern (new action follows same pattern)

### Related Code
- `lambdas/execution_starter/handler.py` - Existing execution queueing logic
- `lambdas/action_http_request/handler.py` - Pattern for action Lambda structure
- `cdk/stacks/api_stack.py` - Where to add webhook route
- `cdk/stacks/execution_stack.py` - Where to add notify action Lambda

### Dependencies
- **Requires:** Phase 2 complete (execution engine functional)
- **Blocks:** Phase 3 triggers (cron, manual UI button), Phase 4 polish

### Assumptions
1. Webhook URL containing workflow_id is sufficient security for personal use (ULID is hard to guess)
2. Discord webhook URL can be hardcoded initially, secrets interpolation (`{{secrets.discord_webhook}}`) for production
3. Discord rate limits (30 requests/minute) are not a concern for personal use
4. All webhook payloads fit in memory (no streaming needed)

---

## Technical Specification

### Data Models

No new DynamoDB tables or models required. The existing Execution model already supports:
- `trigger_type` field (will use "webhook")
- `trigger_data` field (will contain webhook payload, headers, query params)

Webhook trigger data structure:
```python
{
    "type": "webhook",
    "payload": {...},              # Parsed JSON or form data
    "headers": {"User-Agent": "GitHub-Hookshot/..."},
    "query": {"token": "abc"},     # Query string parameters
    "method": "POST",
    "timestamp": "2025-12-16T10:00:00Z"
}
```

Notify action config schema:
```python
{
    "type": "notify",
    "config": {
        "service": "discord",
        "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
        "message": "{{trigger.payload.repository.name}} received push"
    }
}
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /webhook/{workflow_id} | Receive webhook and queue execution |

**Request:**
- Body: JSON or form-urlencoded
- Query params: Optional, passed to trigger_data
- Headers: Passed to trigger_data (excluding AWS-specific headers)

**Response (202):**
```json
{
    "execution_id": "ex_01HQ...",
    "status": "queued",
    "workflow_id": "wf_abc123"
}
```

**Error Responses:**
- 404: Workflow not found
- 400: Workflow disabled
- 500: Internal error (with error message)

### Architecture Diagram

```
                              ┌─────────────────────────────┐
                              │   External Service          │
                              │   (GitHub, Stripe, etc.)    │
                              └──────────────┬──────────────┘
                                             │ POST /webhook/{workflow_id}
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API Gateway (HTTP API)                         │
│  Existing routes: /workflows, /executions                               │
│  NEW: POST /webhook/{workflow_id}                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
    ┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
    │   API Handler    │          │  Webhook Receiver │          │   (Future)       │
    │   Lambda (CRUD)  │          │  Lambda (NEW)     │          │                  │
    └──────────────────┘          └─────────┬────────┘          └──────────────────┘
                                            │
                                            │ SQS SendMessage
                                            ▼
                              ┌─────────────────────────┐
                              │   Execution Queue       │
                              │   (existing)            │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   Execution Starter     │
                              │   (existing)            │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   Step Functions        │
                              │   (add notify route)    │
                              └────────────┬────────────┘
                                           │
       ┌───────────────────────────────────┼───────────────────────────────────┐
       ▼                       ▼           ▼           ▼                       ▼
┌─────────────┐         ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ HTTP Request│         │  Transform  │ │    Log      │ │   Notify    │ │  (Future)   │
│   Action    │         │   Action    │ │   Action    │ │  Action NEW │ │             │
└─────────────┘         └─────────────┘ └─────────────┘ └──────┬──────┘ └─────────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │   Discord Webhook   │
                                                    └─────────────────────┘
```

### Configuration

Environment variables for Webhook Receiver Lambda:
```python
WORKFLOWS_TABLE_NAME = "dev-Workflows"
EXECUTION_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/..."
ENVIRONMENT = "dev"
```

Environment variables for Notify Action Lambda:
```python
EXECUTIONS_TABLE_NAME = "dev-Executions"
ENVIRONMENT = "dev"
```

---

## Implementation Steps

### Phase 1: Webhook Receiver Lambda

#### Step 1.1: Create Webhook Receiver Lambda
**Files:** `lambdas/webhook_receiver/handler.py`, `lambdas/webhook_receiver/requirements.txt`
**Description:** Create the webhook receiver Lambda that accepts POST requests and queues executions.

```python
# handler.py structure
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

logger = Logger(service="webhook-receiver")
tracer = Tracer(service="webhook-receiver")
app = APIGatewayHttpResolver()

@app.post("/webhook/<workflow_id>")
@tracer.capture_method
def receive_webhook(workflow_id: str):
    # 1. Validate workflow exists and is enabled
    # 2. Parse body (JSON or form-urlencoded)
    # 3. Build trigger_data with payload, headers, query, timestamp
    # 4. Send message to SQS execution queue
    # 5. Return 202 with execution_id
    pass

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    return app.resolve(event, context)
```

**Validation:** Lambda deploys and handles POST with test payload

#### Step 1.2: Add Webhook Route to API Gateway
**Files:** `cdk/stacks/api_stack.py`
**Description:** Add the webhook receiver Lambda and route to existing HTTP API.

Changes to `api_stack.py`:
1. Accept `execution_queue` parameter (already exists)
2. Create webhook_receiver Lambda with `_create_webhook_receiver()` method
3. Add route `POST /webhook/{workflow_id}` with new Lambda integration

**Validation:** `cdk synth` succeeds, route appears in CloudFormation output

#### Step 1.3: Create Unit Tests
**Files:** `lambdas/webhook_receiver/tests/test_handler.py`
**Description:** Unit tests for webhook parsing and validation.

Test cases:
- JSON body parsing
- Form-urlencoded body parsing
- Missing workflow returns 404
- Disabled workflow returns 400
- Headers extracted correctly
- Query params extracted correctly
- SQS message sent with correct format

**Validation:** `pytest lambdas/webhook_receiver/tests -v` passes

### Phase 2: Notify Action Lambda

#### Step 2.1: Create Notify Action Lambda
**Files:** `lambdas/action_notify/handler.py`, `lambdas/action_notify/requirements.txt`
**Description:** Create the notify action that posts to Discord.

```python
# handler.py structure (follows action_http_request pattern)
from aws_lambda_powertools import Logger, Tracer
from shared.interpolation import interpolate

logger = Logger(service="action-notify")
tracer = Tracer(service="action-notify")

DISCORD_MAX_LENGTH = 2000

@tracer.capture_method
def execute_notify(config: dict, context: dict) -> dict:
    """Execute notification with interpolated values."""
    service = config.get("service", "discord")

    if service == "discord":
        return execute_discord_notify(config, context)
    else:
        raise ValueError(f"Unknown notify service: {service}")

def execute_discord_notify(config: dict, context: dict) -> dict:
    webhook_url = interpolate(config.get("webhook_url", ""), context)
    message = interpolate(config.get("message", ""), context)

    # Truncate if needed
    if len(message) > DISCORD_MAX_LENGTH:
        message = message[:DISCORD_MAX_LENGTH - 3] + "..."

    response = requests.post(webhook_url, json={"content": message})

    return {
        "status_code": response.status_code,
        "message_sent": message[:100],  # Truncate for logging
        "truncated": len(message) > DISCORD_MAX_LENGTH,
    }

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    # Same pattern as action_http_request
    pass
```

**Validation:** Lambda deploys and posts test message to Discord

#### Step 2.2: Add Notify Action to Step Functions
**Files:** `cdk/stacks/execution_stack.py`
**Description:** Add notify Lambda and update state machine routing.

Changes to `execution_stack.py`:
1. Create notify Lambda in `_create_action_lambdas()`
2. Add `notify_task = tasks.LambdaInvoke(...)`
3. Add route in `RouteByStepType` Choice state for `"notify"` type
4. Chain `notify_task.next(check_step_result)`

**Validation:** `cdk synth` succeeds, state machine definition includes notify

#### Step 2.3: Create Unit Tests
**Files:** `lambdas/action_notify/tests/test_handler.py`
**Description:** Unit tests for notify action.

Test cases:
- Discord message posted successfully
- Message truncation at 2000 chars
- Variable interpolation works
- Invalid webhook URL handled
- Network error handled gracefully

**Validation:** `pytest lambdas/action_notify/tests -v` passes

### Phase 3: Integration and Deployment

#### Step 3.1: Deploy and Test End-to-End
**Files:** None (deployment)
**Description:** Deploy stack and test full webhook → notify flow.

Steps:
1. `cd cdk && cdk deploy --all`
2. Create test workflow with transform + notify steps
3. Send curl request to webhook endpoint
4. Verify Discord message appears
5. Verify execution history shows webhook trigger

**Validation:** Discord message appears with formatted content

#### Step 3.2: Test with Real GitHub Webhook
**Files:** None (testing)
**Description:** Configure GitHub webhook and verify integration.

Steps:
1. Create workflow for GitHub push events
2. Add webhook URL to GitHub repository settings
3. Push a commit
4. Verify Discord notification

**Validation:** GitHub push triggers Discord notification

---

## Testing Requirements

### Unit Tests

#### Webhook Receiver Tests (`lambdas/webhook_receiver/tests/test_handler.py`)
- [ ] `test_json_body_parsing()` - JSON body correctly parsed
- [ ] `test_form_body_parsing()` - Form-urlencoded body correctly parsed
- [ ] `test_raw_body_fallback()` - Unknown content-type stored as raw
- [ ] `test_workflow_not_found()` - Returns 404 for missing workflow
- [ ] `test_workflow_disabled()` - Returns 400 for disabled workflow
- [ ] `test_headers_extracted()` - Headers included in trigger_data
- [ ] `test_query_params_extracted()` - Query params included in trigger_data
- [ ] `test_sqs_message_format()` - SQS message has correct structure
- [ ] `test_execution_id_returned()` - Response includes execution_id

#### Notify Action Tests (`lambdas/action_notify/tests/test_handler.py`)
- [ ] `test_discord_success()` - Message posted successfully
- [ ] `test_message_truncation()` - Long messages truncated to 2000 chars
- [ ] `test_variable_interpolation()` - `{{trigger.*}}` replaced correctly
- [ ] `test_invalid_webhook_url()` - Returns error for bad URL
- [ ] `test_network_error()` - Handles connection failures gracefully
- [ ] `test_discord_rate_limit()` - Handles 429 response appropriately

### Integration Tests
- [ ] `test_webhook_to_sqs()` - Webhook Lambda sends correct SQS message
- [ ] `test_notify_with_secrets()` - Notify uses `{{secrets.discord_webhook}}`

### Manual Testing
1. Create workflow: `{ steps: [{ type: "transform", config: { template: "Hello {{trigger.payload.name}}" }}, { type: "notify", config: { service: "discord", webhook_url: "...", message: "{{steps.format.output.result}}" }}]}`
2. `curl -X POST -H "Content-Type: application/json" -d '{"name": "World"}' https://.../webhook/{workflow_id}`
3. Verify Discord shows "Hello World"

---

## Error Handling

### Expected Errors

| Error | Cause | Handling |
|-------|-------|----------|
| WorkflowNotFound | Invalid workflow_id | Return 404 with message |
| WorkflowDisabled | Workflow enabled=false | Return 400 with message |
| InvalidContentType | Unparseable body | Store as raw string in payload.raw |
| DiscordRateLimit | Too many requests | Return failed status with 429 error |
| DiscordError | Webhook URL invalid | Return failed status with HTTP error |
| InterpolationError | Missing variable | Return failed status with details |

### Edge Cases
1. **Empty body**: Store `payload: {}`, execute normally
2. **Very large body**: API Gateway has 10MB limit, sufficient for webhooks
3. **Binary body**: Store as base64 in `payload.raw_base64`
4. **Concurrent webhooks**: SQS handles ordering, each queued separately
5. **Discord embed vs content**: Initial MVP uses `content` only, embeds in Phase 4

### Rollback Plan
- Delete webhook route from API Gateway via CDK
- Notify action can remain (unused step types are skipped)
- No database migrations to roll back

---

## Performance Considerations

- **Expected latency:** Webhook response <100ms (just queue + 202)
- **Discord notify:** <1s typically (external API call)
- **Throughput:** SQS handles bursts, Discord rate limit is 30/min per webhook
- **Lambda memory:** 256MB sufficient (same as other actions)
- **Lambda timeout:** Webhook 10s (just queueing), Notify 30s (HTTP call)

---

## Security Considerations

- [x] Input validation - Workflow ID validated against DynamoDB
- [x] No secrets in code - Discord webhook URL via config or `{{secrets.*}}`
- [x] Least privilege IAM - Webhook Lambda only needs SQS:SendMessage + DynamoDB:GetItem
- [ ] Webhook signature verification - Deferred to Phase 4 (acceptable for personal use)
- [x] CORS - Not needed for server-to-server webhooks
- [x] Content-Type validation - Accept common types, fallback to raw

**Note on security:** The webhook URL contains the workflow_id (ULID format like `wf_01HQXYZ...`). ULIDs are not cryptographically random but have ~80 bits of entropy per ms, making brute-force impractical. For personal use, this is acceptable. Production would add HMAC signature verification.

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +2 functions, ~1000 invocations/month | ~$0.02 |
| API Gateway | +1 route, ~1000 requests/month | ~$0.01 |
| SQS | Same queue, +1000 messages/month | ~$0.00 |

**Total estimated monthly impact:** <$0.05

---

## Open Questions

1. [x] Should webhook_receiver be a separate Lambda or share with api_handler?
   - **Decision:** Separate Lambda for clarity and isolation

2. [ ] Should we store the webhook URL path in the workflow record for display in UI?
   - **Recommendation:** Not for MVP. URL is predictable: `{api_endpoint}/webhook/{workflow_id}`

3. [x] Any security headers we should return (CORS for browser-based webhooks)?
   - **Decision:** No CORS needed - webhooks are server-to-server. GitHub/Stripe don't need CORS.

4. [ ] Should notify action support Discord embeds for richer formatting?
   - **Recommendation:** Defer to Phase 4. Plain text `content` sufficient for MVP.

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined in INITIAL-005, clear success criteria |
| Feasibility | 10 | Follows existing patterns exactly, no new infrastructure |
| Completeness | 9 | All components covered, testing plan complete |
| Alignment | 10 | Matches PLANNING.md Phase 3, uses existing architecture |
| **Overall** | **9.5** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-16 | Claude | Initial draft from INITIAL-005-webhook-notify.md |
