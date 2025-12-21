# PRP-013: Polling Trigger

> **Status:** Ready
> **Created:** 2025-12-21
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
Users need to trigger workflows based on changes to external URLs/feeds. Currently, only webhook (push) and cron (time-based) triggers exist. Polling enables "pull" triggers for RSS/Atom feeds and generic HTTP content monitoring.

### Proposed Solution
Add a polling trigger type that:
1. Checks URLs on a configurable interval using EventBridge scheduled rules
2. Detects changes via RSS/Atom item tracking or HTTP content hashing
3. Triggers workflow execution when new content is found
4. Auto-disables workflows after repeated failures with Discord notification

### Out of Scope
- Feed autodiscovery from HTML pages
- OAuth/authenticated URLs
- Custom headers for polling requests
- Conditional GET (ETag/If-Modified-Since) optimizations
- WebSub/PubSubHubbub support

---

## Success Criteria

- [ ] Can create workflow with poll trigger (RSS, Atom, or HTTP type)
- [ ] EventBridge rule created with configurable interval (min 5 minutes)
- [ ] RSS/Atom feeds: New items detected and passed to execution
- [ ] HTTP content: Changes detected via SHA256 hash comparison
- [ ] Poll state persisted in DynamoDB (seen items, last hash)
- [ ] Workflow auto-disabled after 4 consecutive failures
- [ ] Discord notification sent on auto-disable
- [ ] Frontend poll trigger configuration UI works
- [ ] Unit tests achieve 80%+ coverage

**Definition of Done:**
- All success criteria met
- Tests written and passing (target: 20+ unit tests)
- Code reviewed
- Documentation updated (TASK.md, DECISIONS.md)
- Deployed and tested end-to-end

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture shows Poller Lambda, poll_state table
- `docs/DECISIONS.md` - ADR-010 (EventBridge InputTransformer pattern)
- `INITIAL/INITIAL-013-polling-trigger.md` - Original feature request

### Related Code
- `lambdas/cron_handler/handler.py` - Pattern for scheduled trigger Lambda
- `lambdas/api/eventbridge.py` - EventBridge rule management utilities
- `cdk/stacks/triggers_stack.py` - Cron handler Lambda definition
- `cdk/stacks/database_stack.py` - PollState table already exists
- `frontend/src/components/WorkflowForm/TriggerConfig.tsx` - Trigger UI component
- `frontend/src/types/workflow.ts` - Type definitions (already has `poll` type)

### Dependencies
- **Requires:** feedparser Python library (RSS/Atom parsing)
- **Requires:** PollState DynamoDB table (already exists)
- **Blocks:** None

### Assumptions
1. Minimum polling interval of 5 minutes is acceptable (avoids excessive Lambda/EventBridge costs)
2. RSS/Atom feeds use standard `<guid>`/`<id>` elements for item identification
3. Discord webhook URL available via DISCORD_WEBHOOK_URL environment variable for failure notifications
4. Seen item IDs list won't exceed DynamoDB item size limit (400KB) - realistic for most feeds

---

## Technical Specification

### Data Models

```python
# Poll State (DynamoDB - already exists)
{
    "workflow_id": "wf_abc123",           # PK
    "last_checked_at": "2025-12-21T10:30:00Z",
    "last_content_hash": "abc123...",     # For HTTP type
    "seen_item_ids": ["id1", "id2"],      # For RSS/Atom
    "consecutive_failures": 0,
    "last_error": None
}

# Poll Trigger Configuration (in Workflow.trigger)
{
    "type": "poll",
    "config": {
        "url": "https://example.com/feed.xml",
        "interval_minutes": 15,           # Min 5, default 15
        "content_type": "rss"             # "rss" | "atom" | "http"
    }
}

# Trigger Data (passed to execution)
# For RSS/Atom:
{
    "type": "poll",
    "content_type": "rss",
    "items": [
        {"title": "...", "link": "...", "guid": "...", "published": "..."}
    ]
}

# For HTTP:
{
    "type": "poll",
    "content_type": "http",
    "content": "<response body>",
    "content_hash": "<sha256>"
}
```

### API Changes

No new API endpoints. Existing endpoints extended:

| Method | Endpoint | Change |
|--------|----------|--------|
| POST | /workflows | Create EventBridge rule for poll triggers |
| PUT | /workflows/{id} | Update EventBridge rule if poll config changes |
| DELETE | /workflows/{id} | Delete poll EventBridge rule |
| PATCH | /workflows/{id}/enabled | Enable/disable poll EventBridge rule |

### Architecture Diagram
```
EventBridge Rule (rate expression)
        │
        ▼
┌─────────────────┐      ┌─────────────┐
│  Poller Lambda  │─────▶│  PollState  │
│                 │◀─────│  (DynamoDB) │
└────────┬────────┘      └─────────────┘
         │
         │ (if new content)
         ▼
┌─────────────────┐
│   SQS Queue     │
│ (execution-queue)│
└────────┬────────┘
         │
         ▼
   Step Functions
```

### EventBridge Rule Configuration
```python
# Rule naming: automations-{env}-{workflow_id}-poll
# Schedule: rate(N minutes) where N >= 5

events_client.put_rule(
    Name=f"automations-{env}-{workflow_id}-poll",
    ScheduleExpression=f"rate({interval} minutes)",
    State="ENABLED",
    Description=f"Polling trigger for workflow {workflow_id}",
)
```

### Configuration
```python
# Environment variables for poller Lambda
WORKFLOWS_TABLE_NAME = "dev-Workflows"
POLL_STATE_TABLE_NAME = "dev-PollState"
EXECUTION_QUEUE_URL = "https://sqs..."
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."  # Optional, for failure notifications
ENVIRONMENT = "dev"
```

---

## Implementation Steps

### Phase 1: Backend - Poller Lambda

#### Step 1.1: Create Poller Lambda Handler
**Files:** `lambdas/poller/handler.py`
**Description:** Main Lambda handler triggered by EventBridge

```python
# Key functions:
def handler(event, context) -> dict:
    """Handle EventBridge scheduled invocation."""
    workflow_id = event.get("workflow_id")
    workflow = get_workflow(workflow_id)
    poll_state = get_poll_state(workflow_id)

    if not workflow or not workflow.get("enabled"):
        return {"status": "skipped"}

    try:
        new_items = poll_url(workflow["trigger"]["config"], poll_state)
        if new_items:
            queue_execution(workflow_id, new_items)
        update_poll_state(workflow_id, poll_state, success=True)
    except Exception as e:
        handle_failure(workflow_id, poll_state, error=str(e))

    return {"status": "completed"}
```

**Validation:** Lambda deploys successfully, can be invoked manually

#### Step 1.2: Implement RSS/Atom Parsing
**Files:** `lambdas/poller/handler.py`
**Description:** Use feedparser to extract new items from feeds

```python
import feedparser

def parse_feed(content: str, content_type: str) -> list[dict]:
    """Parse RSS/Atom feed and return normalized items."""
    feed = feedparser.parse(content)
    items = []
    for entry in feed.entries:
        item = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "guid": entry.get("id") or entry.get("guid") or entry.get("link"),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "")[:500],
        }
        items.append(item)
    return items

def find_new_items(items: list[dict], seen_ids: list[str]) -> list[dict]:
    """Filter to only items not in seen_ids."""
    seen_set = set(seen_ids)
    return [item for item in items if item["guid"] not in seen_set]

MAX_SEEN_ITEMS = 500

def prune_seen_ids(seen_ids: list[str], new_ids: list[str]) -> list[str]:
    """Add new IDs and prune to MAX_SEEN_ITEMS, keeping most recent."""
    combined = seen_ids + new_ids
    return combined[-MAX_SEEN_ITEMS:] if len(combined) > MAX_SEEN_ITEMS else combined
```

**Validation:** Can parse sample RSS and Atom feeds, correctly identify new items

#### Step 1.3: Implement HTTP Content Hashing
**Files:** `lambdas/poller/handler.py`
**Description:** SHA256 hash comparison for generic HTTP content

```python
import hashlib

def hash_content(content: str) -> str:
    """Generate SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()

def check_http_changed(content: str, last_hash: str | None) -> tuple[bool, str]:
    """Check if HTTP content has changed."""
    current_hash = hash_content(content)
    changed = last_hash is None or current_hash != last_hash
    return changed, current_hash
```

**Validation:** Correctly detects content changes

#### Step 1.4: Implement Failure Handling with Auto-Disable
**Files:** `lambdas/poller/handler.py`
**Description:** Track failures, auto-disable after 4, send Discord notification

```python
MAX_CONSECUTIVE_FAILURES = 4

def handle_failure(workflow_id: str, poll_state: dict, error: str) -> None:
    """Handle poll failure, auto-disable after threshold."""
    failures = poll_state.get("consecutive_failures", 0) + 1

    update_poll_state(workflow_id, {
        "consecutive_failures": failures,
        "last_error": error,
        "last_checked_at": now_iso(),
    })

    if failures >= MAX_CONSECUTIVE_FAILURES:
        disable_workflow(workflow_id)
        disable_eventbridge_rule(workflow_id)
        send_discord_notification(workflow_id, error, failures)

def send_discord_notification(workflow_id: str, error: str, failures: int) -> None:
    """Send Discord notification about auto-disabled workflow."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("No DISCORD_WEBHOOK_URL, skipping notification")
        return

    requests.post(webhook_url, json={
        "content": f"⚠️ Workflow `{workflow_id}` auto-disabled after {failures} consecutive polling failures.\nLast error: {error}"
    }, timeout=10)
```

**Validation:** Workflow disabled after 4 failures, Discord notification received

#### Step 1.5: Create Requirements File
**Files:** `lambdas/poller/requirements.txt`

```
aws-lambda-powertools>=2.0.0
aws-xray-sdk>=2.0.0
boto3>=1.26.0
feedparser>=6.0.0
requests>=2.28.0
```

**Validation:** pip install succeeds

### Phase 2: Backend - CDK Infrastructure

#### Step 2.1: Add Poller Lambda to Triggers Stack
**Files:** `cdk/stacks/triggers_stack.py`
**Description:** Create poller Lambda with required permissions

```python
def _create_poller(self) -> None:
    """Create the poller Lambda function."""
    function_name = f"{self.env_name}-automation-poller"

    self.poller = lambda_.Function(
        self, "Poller",
        function_name=function_name,
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="handler.handler",
        code=lambda_.Code.from_asset(...),
        memory_size=256,
        timeout=Duration.seconds(60),  # Needs time to fetch URLs
        environment={
            "WORKFLOWS_TABLE_NAME": ...,
            "POLL_STATE_TABLE_NAME": ...,
            "EXECUTION_QUEUE_URL": ...,
            "DISCORD_WEBHOOK_URL": ...,  # Optional
        },
    )

    # Permissions
    self.workflows_table.grant_read_write_data(self.poller)
    self.poll_state_table.grant_read_write_data(self.poller)
    self.execution_queue.grant_send_messages(self.poller)

    # EventBridge invoke permission
    self.poller.add_permission(
        "EventBridgeInvoke",
        principal=iam.ServicePrincipal("events.amazonaws.com"),
    )

    # EventBridge rule management for auto-disable
    self.poller.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["events:DisableRule"],
        resources=[f"arn:aws:events:{region}:{account}:rule/automations-*-poll"],
    ))
```

**Validation:** CDK synth succeeds, stack deploys

#### Step 2.2: Export Poller Lambda ARN
**Files:** `cdk/stacks/triggers_stack.py`

```python
CfnOutput(
    self, "PollerArn",
    value=self.poller.function_arn,
    export_name=f"{environment}-automation-poller-arn",
)
```

**Validation:** ARN exported and accessible

### Phase 3: Backend - API Updates

#### Step 3.1: Extend eventbridge.py for Poll Triggers
**Files:** `lambdas/api/eventbridge.py`
**Description:** Add poll rule management alongside cron

```python
POLLER_ARN = os.environ.get("POLLER_LAMBDA_ARN", "")

def get_poll_rule_name(workflow_id: str) -> str:
    return f"automations-{ENV}-{workflow_id}-poll"

def create_poll_rule(workflow_id: str, interval_minutes: int) -> None:
    """Create EventBridge rule for poll trigger."""
    rule_name = get_poll_rule_name(workflow_id)
    schedule = f"rate({interval_minutes} minutes)" if interval_minutes > 1 else "rate(1 minute)"

    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule,
        State="ENABLED",
        Description=f"Polling trigger for workflow {workflow_id}",
    )

    events_client.put_targets(
        Rule=rule_name,
        Targets=[{
            "Id": "poller",
            "Arn": POLLER_ARN,
            "InputTransformer": {
                "InputPathsMap": {"time": "$.time"},
                "InputTemplate": '{"workflow_id": "' + workflow_id + '", "time": <time>}',
            },
        }],
    )

def delete_poll_rule(workflow_id: str) -> None:
    """Delete EventBridge poll rule."""
    # Similar to delete_schedule_rule but for poll rules
    ...

def sync_workflow_rule(...) -> None:
    """Extended to handle both cron and poll triggers."""
    old_type = (old_trigger or {}).get("type")
    new_type = (new_trigger or {}).get("type")

    # Handle cron rules (existing)
    ...

    # Handle poll rules
    if new_type == "poll":
        interval = new_trigger.get("config", {}).get("interval_minutes", 15)
        create_poll_rule(workflow_id, interval)
    elif old_type == "poll":
        delete_poll_rule(workflow_id)
```

**Validation:** Poll rules created/deleted when saving poll-type workflows

#### Step 3.2: Add POLLER_LAMBDA_ARN to API Lambda Environment
**Files:** `cdk/stacks/api_stack.py`

Add environment variable from triggers stack export.

**Validation:** API Lambda has access to poller ARN

### Phase 4: Frontend

#### Step 4.1: Update TriggerConfig Component
**Files:** `frontend/src/components/WorkflowForm/TriggerConfig.tsx`
**Description:** Add poll trigger configuration UI

```tsx
{/* Add to trigger type dropdown */}
<option value="poll">Poll (RSS/HTTP)</option>

{/* Poll config section */}
{triggerType === 'poll' && (
  <div className="space-y-4">
    <div>
      <label>URL to Poll</label>
      <input {...register('trigger.config.url', { required: true })} />
    </div>

    <div>
      <label>Content Type</label>
      <select {...register('trigger.config.content_type')}>
        <option value="rss">RSS Feed</option>
        <option value="atom">Atom Feed</option>
        <option value="http">HTTP (detect any change)</option>
      </select>
    </div>

    <div>
      <label>Poll Interval (minutes)</label>
      <input
        type="number"
        min={5}
        defaultValue={15}
        {...register('trigger.config.interval_minutes', { min: 5 })}
      />
      <p className="text-xs">Minimum: 5 minutes</p>
    </div>
  </div>
)}
```

**Validation:** Can configure poll trigger in UI, form validation works

#### Step 4.2: Update TypeScript Types
**Files:** `frontend/src/types/workflow.ts`
**Description:** Add poll config to TriggerFormData

```typescript
export interface TriggerFormData {
  type: 'manual' | 'webhook' | 'cron' | 'poll';
  config: {
    schedule?: string;       // For cron
    url?: string;            // For poll
    interval_minutes?: number;  // For poll
    content_type?: 'rss' | 'atom' | 'http';  // For poll
  };
}
```

**Validation:** TypeScript compiles without errors

### Phase 5: Testing

#### Step 5.1: Create Poller Unit Tests
**Files:** `lambdas/poller/tests/test_handler.py`

Tests:
- `test_parse_rss_feed()` - Parse standard RSS
- `test_parse_atom_feed()` - Parse Atom with id elements
- `test_parse_atom_feed_fallback_link()` - Fallback to link when no id
- `test_find_new_items()` - Filter seen items correctly
- `test_hash_content()` - SHA256 hashing
- `test_check_http_changed()` - Detect content changes
- `test_handle_failure_increments_counter()` - Failure tracking
- `test_auto_disable_after_four_failures()` - Auto-disable logic
- `test_send_discord_notification()` - Discord webhook called
- `test_skip_disabled_workflow()` - Skip if not enabled
- `test_skip_wrong_trigger_type()` - Safety check
- `test_prune_seen_ids()` - Prune to 500 entries

**Validation:** pytest passes, coverage > 80%

---

## Testing Requirements

### Unit Tests
- [ ] RSS feed parsing (standard, edge cases)
- [ ] Atom feed parsing (with id, fallback to link)
- [ ] New item detection
- [ ] HTTP hash comparison
- [ ] Consecutive failure counting
- [ ] Auto-disable after 4 failures
- [ ] Discord notification sending
- [ ] EventBridge rule creation for poll type
- [ ] Poll state persistence

### Integration Tests
- [ ] Create workflow with poll trigger → EventBridge rule created
- [ ] Update poll interval → EventBridge rule updated
- [ ] Delete poll workflow → EventBridge rule deleted
- [ ] Enable/disable poll workflow → EventBridge rule state matches

### Manual Testing
1. Create workflow with RSS feed URL (e.g., Hacker News)
2. Wait for first poll, verify poll_state populated
3. Verify execution created when new items appear
4. Test with invalid URL, verify failure counting
5. Verify auto-disable after 4 failures
6. Check Discord notification received

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| ConnectionError | URL unreachable | Increment failure counter |
| TimeoutError | Slow response | Increment failure counter |
| ParseError | Malformed feed | Increment failure counter |
| DynamoDB throttle | High load | Retry with backoff |

### Edge Cases
1. **Empty feed:** No items to process, update last_checked_at only
2. **Very large feed:** Limit to first 100 items to avoid DynamoDB item size limits
3. **Missing guid/id:** Fall back to link as identifier
4. **Duplicate items:** seen_item_ids handles deduplication
5. **Workflow deleted mid-poll:** Log warning, skip execution

### Rollback Plan
1. Disable all poll EventBridge rules via console
2. Roll back CDK deployment
3. Poll state in DynamoDB is safe to leave (will be ignored)

---

## Performance Considerations

- **Expected latency:** 2-5 seconds per poll (URL fetch + parse + DynamoDB)
- **Lambda timeout:** 60 seconds (generous for slow feeds)
- **Memory:** 256 MB (feedparser is lightweight)
- **Concurrent executions:** One per workflow, not a concern at personal scale

---

## Security Considerations

- [x] Input validation: URL must be https (or http with warning)
- [x] No secrets in code (Discord webhook via env var)
- [x] Least privilege IAM (only poll_state + workflows tables)
- [ ] Consider: Rate limiting per domain to avoid abuse
- [ ] Consider: User-agent header to identify bot

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +N polls * 5s * $0.0000166/GB-s | ~$0.10 |
| EventBridge | +N rules * $1/million invocations | ~$0.01 |
| DynamoDB | +N reads/writes per poll | ~$0.05 |
| External requests | feedparser fetches | $0 |

**Total estimated monthly impact:** ~$0.20 for 10 workflows polling every 15 min

---

## Open Questions

1. [x] ~~Use feedparser or write custom parser?~~ → Use feedparser (well-maintained)
2. [x] ~~Should poll state include full last-fetched content for debugging?~~ → No, keep lean. Content available via re-fetch.
3. [x] ~~Maximum seen_item_ids list size before pruning old entries?~~ → 500 entries, prune oldest when exceeded.
4. [x] ~~Should HTTP polling include response headers in trigger_data?~~ → No for MVP, can add later.

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements well-defined in INITIAL file |
| Feasibility | 9 | Follows existing cron pattern closely |
| Completeness | 9 | All questions resolved |
| Alignment | 9 | Fits architecture, within budget |
| **Overall** | **9.0** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-21 | Claude | Initial draft |
| 2025-12-21 | Claude | Resolved open questions: no debug content, 500 max seen_ids, no headers |
