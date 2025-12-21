# Polling Trigger

## Overview
Add polling trigger type that checks URLs on a configurable interval and triggers workflow execution when content changes.

## Requirements

### Trigger Configuration
```json
{
  "type": "poll",
  "config": {
    "url": "https://example.com/feed.xml",
    "interval_minutes": 15,
    "content_type": "rss" | "atom" | "http"
  }
}
```
- `interval_minutes`: User-configurable, default 15, minimum 5
- `content_type`: RSS/Atom (track seen items) or HTTP (hash comparison)

### Change Detection
- **RSS/Atom**: Parse feed, compare item GUIDs/IDs against `seen_item_ids`, trigger for new items
- **Atom**: Use `<id>` element, fall back to `<link>` if no id
- **RSS**: Use `<guid>` element, fall back to `<link>` if no guid
- **HTTP**: SHA256 hash of response body, trigger if hash differs from `last_content_hash`

### Poll State (DynamoDB)
Table already exists in database_stack.py. Schema:
```python
{
    "workflow_id": "wf_abc123",           # PK
    "last_checked_at": "2025-01-15T10:30:00Z",
    "last_content_hash": "abc123...",
    "seen_item_ids": ["item1", "item2"],
    "consecutive_failures": 0,
    "last_error": null
}
```

### Error Handling
- Track `consecutive_failures` counter in poll_state table
- After 4 consecutive failures:
  1. Disable the workflow (set `enabled: false` in workflows table)
  2. Disable the EventBridge rule
  3. Send Discord notification using DISCORD_WEBHOOK_URL env var (same pattern as notify action)
- Reset counter to 0 on successful poll
- Store last error message in `last_error` field

### Trigger Data Passed to Execution
- **RSS/Atom**: `{"type": "poll", "content_type": "rss|atom", "items": [<new items as dicts>]}`
- **HTTP**: `{"type": "poll", "content_type": "http", "content": "<response body>", "content_hash": "<sha256>"}`

### Infrastructure
- **Poller Lambda**: Triggered by EventBridge, polls URL, detects changes, queues execution
- **EventBridge rules**: Per-workflow, rate expression `rate(N minutes)`
- **Rule naming**: `automation-poll-{workflow_id}` (consistent with cron pattern)
- **IAM**: Lambda needs SQS send, DynamoDB read/write (workflows + poll_state tables), EventBridge rule management

### API Updates
- Workflow create: Create EventBridge rule for poll triggers (like cron)
- Workflow update: Update/recreate EventBridge rule if poll config changes
- Workflow enable/disable: Enable/disable poll EventBridge rule (extend existing PATCH handler)
- Workflow delete: Delete poll EventBridge rule (extend existing DELETE handler)

### Frontend Updates
- Add "Poll" option to trigger type dropdown in TriggerConfig component
- Add poll config fields: url, interval_minutes (number input, default 15, min 5), content_type (dropdown: rss/atom/http)
- Display poll-specific info on workflow detail page

## Files to Create/Modify

### New Files
- `lambdas/poller/handler.py` - Poller Lambda handler
- `lambdas/poller/requirements.txt` - feedparser, requests, aws-lambda-powertools, aws-xray-sdk
- `lambdas/poller/tests/test_handler.py` - Unit tests

### Modified Files
- `cdk/stacks/triggers_stack.py` - Add poller Lambda, grant permissions
- `lambdas/api/handler.py` - EventBridge rule management for poll type in create/update/delete/toggle
- `frontend/src/components/workflow/TriggerConfig.tsx` - Add poll trigger UI

## Testing

### Unit Tests
- Parse RSS feed, extract new items
- Parse Atom feed, extract new items  
- HTTP hash change detection
- Consecutive failure counting
- Auto-disable after 4 failures

### Integration Tests
1. Create workflow with RSS feed URL, verify EventBridge rule created
2. Manually invoke poller, verify poll_state created with seen_item_ids
3. Add new item to feed (or use test feed), verify execution triggers
4. Change generic HTTP content, verify execution triggers with new hash
5. Simulate 4 failures (invalid URL), verify:
   - Workflow disabled in DynamoDB
   - EventBridge rule disabled
   - Discord notification sent
6. Enable/disable workflow, verify EventBridge rule state matches
7. Delete workflow, verify EventBridge rule deleted

## Dependencies
- `feedparser` - RSS/Atom parsing library (well-maintained, handles edge cases)
- `requests` - HTTP client (already used elsewhere)

## Out of Scope
- Feed autodiscovery from HTML pages
- OAuth/authenticated URLs
- Custom headers for polling requests
- Conditional GET (ETag/If-Modified-Since) - could add later for efficiency
