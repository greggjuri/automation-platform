# INITIAL-005: Webhook Trigger + Notify Action

## What I Want

Add webhook triggers so external services can trigger workflows via HTTP POST, and add a Notify action that posts messages to Discord. This enables the first real end-to-end automation: external event → process → notification.

## Why

- **Webhook trigger**: GitHub, Stripe, home automation, etc. can trigger workflows by POSTing to a URL
- **Notify action**: Workflows need to produce visible output - Discord is my primary notification channel
- **Together**: Enables useful automations like "GitHub push → format message → Discord notification"

## User Stories

1. As a user, I want to give GitHub a webhook URL so new commits trigger my workflow
2. As a user, I want my workflow to post formatted messages to my Discord channel
3. As a user, I want webhook payloads available as `{{trigger.*}}` in my workflow steps
4. As a user, I want to see webhook-triggered executions in my execution history

## Current State

- ✅ Execution engine works (SQS → Step Functions → Action Lambdas)
- ✅ API Gateway HTTP API exists at `https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com`
- ✅ Actions exist: `http_request`, `transform`, `log`
- ✅ Variable interpolation works with `{{trigger.*}}` and `{{steps.*}}`
- ✅ Frontend shows execution history
- ❌ No webhook endpoint yet
- ❌ No Discord/notify action yet

## Proposed Solution

### 1. Webhook Receiver Lambda

New Lambda that handles `POST /webhook/{workflow_id}`:

```python
# Pseudocode
def handler(event):
    workflow_id = event["pathParameters"]["workflow_id"]
    
    # Get workflow from DynamoDB
    workflow = get_workflow(workflow_id)
    if not workflow:
        return 404
    if not workflow.get("enabled", True):
        return 400, "Workflow is disabled"
    
    # Extract trigger data from request
    trigger_data = {
        "type": "webhook",
        "payload": parse_body(event),  # JSON or form data
        "headers": event.get("headers", {}),
        "query": event.get("queryStringParameters", {}),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Queue execution (same as manual trigger)
    execution_id = f"exec_{ulid()}"
    sqs.send_message(
        queue_url=EXECUTION_QUEUE_URL,
        message_body=json.dumps({
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "trigger_data": trigger_data
        })
    )
    
    # Return immediately (async execution)
    return 202, {"execution_id": execution_id, "status": "queued"}
```

### 2. Notify Action Lambda

New action Lambda for Discord (extensible to other services later):

```python
# Config schema
{
    "type": "notify",
    "config": {
        "service": "discord",  # Future: slack, email, pushover
        "webhook_url": "{{secrets.discord_webhook}}",  # or hardcoded for testing
        "message": "{{trigger.payload.repository.name}} received push from {{trigger.payload.sender.login}}"
    }
}

# Lambda posts to Discord
def handler(event):
    config = event["config"]
    context = event["context"]
    
    webhook_url = interpolate(config["webhook_url"], context)
    message = interpolate(config["message"], context)
    
    response = requests.post(webhook_url, json={
        "content": message,
        # Optional: embeds for rich formatting
    })
    
    return {
        "status": "success" if response.ok else "failed",
        "output": {
            "status_code": response.status_code,
            "message_sent": message[:100]  # Truncate for logging
        }
    }
```

### 3. API Gateway Route

Add route to existing HTTP API:
- `POST /webhook/{workflow_id}` → Webhook Receiver Lambda

### 4. Step Functions Update

Add `notify` to the RouteByStepType choice state (same pattern as existing actions).

## Example Test Workflow

```json
{
    "name": "GitHub Push to Discord",
    "trigger": {
        "type": "webhook"
    },
    "steps": [
        {
            "id": "format",
            "name": "Format Message",
            "type": "transform",
            "config": {
                "template": "🚀 **{{trigger.payload.repository.name}}** received {{trigger.payload.commits | length}} commit(s) from {{trigger.payload.sender.login}}"
            }
        },
        {
            "id": "notify",
            "name": "Send to Discord",
            "type": "notify",
            "config": {
                "service": "discord",
                "webhook_url": "https://discord.com/api/webhooks/xxx/yyy",
                "message": "{{steps.format.output.result}}"
            }
        }
    ]
}
```

Webhook URL to give GitHub:
```
https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com/webhook/{workflow_id}
```

## Technical Considerations

1. **No auth on webhook endpoint** - Anyone with URL can trigger. Acceptable for MVP since:
   - URL contains workflow_id (hard to guess ULID)
   - Workflow must be enabled
   - Can add signature verification later (GitHub, Stripe support HMAC)

2. **Request body parsing** - Support both JSON and form-urlencoded:
   ```python
   content_type = headers.get("content-type", "")
   if "application/json" in content_type:
       payload = json.loads(body)
   elif "application/x-www-form-urlencoded" in content_type:
       payload = parse_qs(body)
   else:
       payload = {"raw": body}
   ```

3. **Discord rate limits** - 30 requests/minute per webhook. Not a concern for personal use.

4. **Discord message limits** - 2000 chars max. Should truncate with warning in output.

## Files to Create/Modify

### New Files
- `lambdas/webhook_receiver/handler.py`
- `lambdas/webhook_receiver/requirements.txt`
- `lambdas/action_notify/handler.py`
- `lambdas/action_notify/requirements.txt`
- `lambdas/action_notify/tests/test_handler.py`
- `lambdas/webhook_receiver/tests/test_handler.py`

### Modify
- `cdk/stacks/api_stack.py` - Add webhook route + Lambda
- `cdk/stacks/execution_stack.py` - Add notify action Lambda, update Step Functions definition
- `cdk/app.py` - Wire up any new dependencies between stacks

## Out of Scope

- Webhook signature verification (Phase 4)
- Slack/email notify services (Phase 4)
- Retry on Discord failure (Phase 4)
- Frontend UI for copying webhook URL (can use API endpoint directly)

## Success Criteria

1. `POST /webhook/{workflow_id}` with JSON body queues execution
2. Execution shows `trigger.type: "webhook"` and `trigger.payload` contains POST body
3. Notify action posts message to Discord channel
4. Full flow works: `curl webhook → transform → discord message appears`

## Questions for Claude

1. Should webhook_receiver be a separate Lambda or can it share with api_handler? (I lean separate for clarity)
2. Should we store the webhook URL path in the workflow record for display in UI?
3. Any security headers we should return (CORS for browser-based webhooks)?
