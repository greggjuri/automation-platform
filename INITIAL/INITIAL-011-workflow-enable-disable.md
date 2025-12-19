# Feature Request: Workflow Enable/Disable Toggle

## Summary
Add ability to enable/disable workflows. Disabled workflows should not execute regardless of trigger type.

## User Story
As a user, I want to temporarily disable a workflow without deleting it, so I can pause automations during maintenance or testing without losing my configuration.

## Current State
- Workflows have an `enabled` field in the data model (PLANNING.md shows `"enabled": True`)
- No UI or API support for toggling this field
- Triggers (cron, webhook, manual) don't check the enabled status

## Requirements

### Backend

1. **API Endpoint**: `PATCH /workflows/{id}/enabled`
   - Request body: `{ "enabled": true | false }`
   - Returns updated workflow
   - Alternative: Could use existing `PUT /workflows/{id}` but dedicated endpoint is cleaner

2. **Cron Trigger Behavior**:
   - When workflow is disabled → disable the EventBridge rule (not delete it)
   - When workflow is enabled → enable the EventBridge rule
   - Use `events_client.disable_rule()` / `enable_rule()` APIs
   - This prevents Lambda invocations entirely when disabled (cost efficient)

3. **Webhook Trigger Behavior**:
   - Webhook receiver Lambda checks `enabled` flag before queuing execution
   - Return `503 Service Unavailable` with message "Workflow is disabled"
   - Alternative: Return `404 Not Found` to not reveal workflow exists (security)

4. **Manual Trigger Behavior**:
   - `POST /workflows/{id}/execute` should check `enabled` flag
   - Return `400 Bad Request` with message "Workflow is disabled"

### Frontend

1. **Workflow Detail Page**:
   - Toggle switch component near workflow name/header
   - Immediate visual feedback (optimistic update or loading state)
   - Toast notification on success/failure

2. **Workflow List/Cards**:
   - Visual indicator for disabled workflows (e.g., "Disabled" badge, dimmed card)
   - Toggle accessible from card actions (optional, detail page is sufficient for MVP)

3. **Run Now Button**:
   - Disabled state when workflow is disabled
   - Tooltip explaining why it's disabled

## Technical Notes

### EventBridge Rule Management
The API Lambda already manages EventBridge rules in `update_workflow()`. Add logic:
```python
# When enabled status changes for cron workflow:
if workflow["trigger"]["type"] == "cron":
    if enabled:
        events_client.enable_rule(Name=rule_name)
    else:
        events_client.disable_rule(Name=rule_name)
```

### Webhook Receiver Update
Add early check in webhook handler:
```python
workflow = get_workflow(workflow_id)
if not workflow:
    return {"statusCode": 404, ...}
if not workflow.get("enabled", True):
    return {"statusCode": 503, "body": "Workflow is disabled"}
```

### Frontend Toggle Component
Glass-style toggle switch matching existing button styling:
- Use existing color scheme (silver/white for enabled, dimmed for disabled)
- Consider using a simple button toggle vs. actual switch component

## Out of Scope
- Bulk enable/disable multiple workflows
- Scheduled enable/disable (e.g., disable during business hours)
- Disable individual steps within a workflow

## Testing
1. Create cron workflow, verify EventBridge rule exists and is enabled
2. Disable workflow via UI, verify EventBridge rule is disabled in AWS Console
3. Re-enable workflow, verify rule is enabled again
4. Create webhook workflow, disable it, send webhook → expect 503
5. Disable workflow, verify "Run Now" button is disabled in UI

## Acceptance Criteria
- [ ] Can toggle workflow enabled/disabled from detail page
- [ ] Disabled workflows show visual indicator in list view
- [ ] Cron workflows: EventBridge rule is disabled (not just ignored)
- [ ] Webhook workflows: Returns 503 when disabled
- [ ] Manual trigger: Run Now button disabled with explanation
- [ ] Toast notifications for toggle success/failure
