# PRP-011: Workflow Enable/Disable Toggle

> **Status:** Ready
> **Created:** 2025-12-19
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
Users cannot temporarily disable workflows without deleting them. When a workflow needs to be paused for maintenance, testing, or debugging, the only option is to delete and recreate it. This is cumbersome and risks losing configuration.

### Proposed Solution
Add the ability to toggle workflow enabled/disabled status. This includes:
1. A dedicated API endpoint for toggling enabled status
2. EventBridge rule state sync for cron triggers (disable rule, not delete it)
3. Webhook receiver and manual execution checks for enabled status
4. UI toggle on the workflow detail page
5. Visual indicators for disabled workflows in the list view

### Out of Scope
- Bulk enable/disable multiple workflows
- Scheduled enable/disable (e.g., disable during business hours)
- Disable individual steps within a workflow

---

## Success Criteria

- [ ] Can toggle workflow enabled/disabled from detail page
- [ ] Disabled workflows show "Disabled" badge in list view
- [ ] Cron workflows: EventBridge rule is disabled (not deleted) when workflow disabled
- [ ] Webhook workflows: Returns 503 when triggered while disabled
- [ ] Manual trigger: "Run Now" button disabled with explanation tooltip
- [ ] Toast notifications for toggle success/failure
- [ ] Unit tests for new API endpoint
- [ ] Unit tests for EventBridge rule state management

**Definition of Done:**
- All success criteria met
- Tests written and passing
- Code reviewed
- Documentation updated
- Deployed to dev/staging

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Workflow data model shows `enabled: True` field
- `docs/DECISIONS.md` - ADR-010: EventBridge InputTransformer for cron triggers

### Related Code
- `lambdas/api/handler.py` - Already checks `enabled` in `execute_workflow_handler` (lines 321-322)
- `lambdas/api/eventbridge.py` - EventBridge rule management, needs enable/disable rule support
- `lambdas/webhook_receiver/handler.py` - Already checks `enabled` status (lines 201-204)
- `frontend/src/pages/WorkflowDetailPage.tsx` - Needs toggle UI
- `frontend/src/components/workflows/WorkflowCard.tsx` - Shows enabled badge already
- `frontend/src/hooks/useWorkflowMutations.ts` - Pattern for new mutation hook

### Dependencies
- **Requires:** Nothing - all infrastructure already exists
- **Blocks:** Nothing

### Assumptions
1. EventBridge rules support `disable_rule()` and `enable_rule()` APIs
2. The frontend will use optimistic updates for better UX
3. A dedicated PATCH endpoint is cleaner than using PUT for just enabled state

---

## Technical Specification

### Data Models

No changes needed - `enabled` field already exists on workflows:

```python
# Existing in DynamoDB workflow item
{
    "workflow_id": "wf_abc123",
    "enabled": True,  # <-- Already exists
    ...
}
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | /workflows/{id}/enabled | Toggle workflow enabled status |

**Request Body:**
```json
{
    "enabled": true | false
}
```

**Response (200):**
```json
{
    "workflow_id": "wf_abc123",
    "enabled": true,
    "message": "Workflow enabled"
}
```

**Error Responses:**
- 404: Workflow not found
- 400: Invalid request body (missing `enabled` field)

### EventBridge Rule State Management

New functions in `eventbridge.py`:

```python
def enable_schedule_rule(workflow_id: str) -> None:
    """Enable the EventBridge rule for a cron workflow."""
    rule_name = get_rule_name(workflow_id)
    events_client.enable_rule(Name=rule_name)

def disable_schedule_rule(workflow_id: str) -> None:
    """Disable the EventBridge rule for a cron workflow."""
    rule_name = get_rule_name(workflow_id)
    events_client.disable_rule(Name=rule_name)
```

### Frontend Components

**Toggle Switch Component:**
- Use existing Button component as base
- Glass styling consistent with existing UI
- Loading state during API call
- Disabled state when request is pending

**WorkflowDetailPage Updates:**
- Add toggle switch next to workflow name
- Disable "Run Now" button when workflow is disabled
- Show tooltip explaining why button is disabled

**WorkflowCard Updates:**
- Already shows enabled/disabled badge (using StatusBadge)
- Optionally add visual dimming for disabled workflows

---

## Implementation Steps

### Phase 1: Backend API

#### Step 1.1: Add EventBridge Enable/Disable Functions
**Files:** `lambdas/api/eventbridge.py`
**Description:** Add `enable_schedule_rule()` and `disable_schedule_rule()` functions.

```python
def enable_schedule_rule(workflow_id: str) -> None:
    """Enable the EventBridge rule for a cron workflow."""
    rule_name = get_rule_name(workflow_id)
    try:
        events_client.enable_rule(Name=rule_name)
        logger.info("EventBridge rule enabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Rule not found, cannot enable", rule_name=rule_name)

def disable_schedule_rule(workflow_id: str) -> None:
    """Disable the EventBridge rule for a cron workflow."""
    rule_name = get_rule_name(workflow_id)
    try:
        events_client.disable_rule(Name=rule_name)
        logger.info("EventBridge rule disabled", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.warning("Rule not found, cannot disable", rule_name=rule_name)
```

**Validation:** Unit tests for new functions.

#### Step 1.2: Add PATCH Endpoint for Enabled Toggle
**Files:** `lambdas/api/handler.py`
**Description:** Add `PATCH /workflows/{id}/enabled` endpoint.

```python
@app.patch("/workflows/<workflow_id>/enabled")
@tracer.capture_method
def toggle_workflow_enabled(workflow_id: str) -> dict:
    """Toggle workflow enabled/disabled status."""
    logger.info("Toggling workflow enabled", workflow_id=workflow_id)

    # Get current workflow
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Parse request body
    body = app.current_event.json_body or {}
    if "enabled" not in body:
        raise BadRequestError("Missing 'enabled' field in request body")

    new_enabled = bool(body["enabled"])
    old_enabled = workflow.get("enabled", True)

    # Update in DynamoDB
    updates = {
        "enabled": new_enabled,
        "updated_at": get_current_timestamp(),
    }
    update_workflow(workflow_id, updates)

    # Sync EventBridge rule if cron trigger
    if workflow.get("trigger", {}).get("type") == "cron":
        try:
            if new_enabled:
                enable_schedule_rule(workflow_id)
            else:
                disable_schedule_rule(workflow_id)
        except Exception as e:
            logger.warning("Failed to sync EventBridge rule state", error=str(e))

    action = "enabled" if new_enabled else "disabled"
    logger.info(f"Workflow {action}", workflow_id=workflow_id)

    return {
        "workflow_id": workflow_id,
        "enabled": new_enabled,
        "message": f"Workflow {action}",
    }
```

**Validation:** `curl -X PATCH .../workflows/{id}/enabled -d '{"enabled": false}'`

#### Step 1.3: Unit Tests for Toggle Endpoint
**Files:** `lambdas/api/tests/test_toggle_enabled.py` (new file)
**Description:** Unit tests for the new endpoint and EventBridge functions.

Tests to include:
- Toggle enabled to disabled (success)
- Toggle disabled to enabled (success)
- Toggle with cron workflow - verifies EventBridge rule state changes
- Toggle with webhook workflow - no EventBridge calls
- 404 for non-existent workflow
- 400 for missing `enabled` field

**Validation:** `pytest lambdas/api/tests/test_toggle_enabled.py -v`

### Phase 2: Frontend UI

#### Step 2.1: Add Toggle Mutation Hook
**Files:** `frontend/src/hooks/useWorkflowMutations.ts`
**Description:** Add `useToggleWorkflowEnabled()` mutation hook.

```typescript
/**
 * Toggle workflow enabled/disabled status.
 */
export function useToggleWorkflowEnabled() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workflowId,
      enabled,
    }: {
      workflowId: string;
      enabled: boolean;
    }): Promise<{ workflow_id: string; enabled: boolean; message: string }> => {
      const response = await apiClient.patch(
        `/workflows/${workflowId}/enabled`,
        { enabled }
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.all });
      queryClient.invalidateQueries({ queryKey: workflowKeys.detail(data.workflow_id) });
    },
  });
}
```

**Validation:** TypeScript compiles without errors.

#### Step 2.2: Create Toggle Switch Component
**Files:** `frontend/src/components/common/ToggleSwitch.tsx` (new file)
**Description:** Glass-styled toggle switch component.

```typescript
interface ToggleSwitchProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
  isLoading?: boolean;
  label?: string;
}

export function ToggleSwitch({ enabled, onChange, disabled, isLoading, label }: ToggleSwitchProps) {
  // Glass-styled toggle with loading state
}
```

**Validation:** Visually matches existing glass UI elements.

#### Step 2.3: Add Toggle to WorkflowDetailPage
**Files:** `frontend/src/pages/WorkflowDetailPage.tsx`
**Description:** Add toggle switch in header, disable "Run Now" when workflow disabled.

Changes:
1. Import `ToggleSwitch` and `useToggleWorkflowEnabled`
2. Add toggle switch next to workflow name
3. Wire up mutation with toast notifications
4. Disable "Run Now" button when `!workflow.enabled`
5. Add tooltip to explain disabled state

**Validation:** Manual testing - toggle workflow, verify EventBridge in AWS Console.

#### Step 2.4: Visual Feedback for Disabled Workflows
**Files:** `frontend/src/components/workflows/WorkflowCard.tsx`
**Description:** Add visual dimming/indicator for disabled workflows.

Changes:
1. Add conditional opacity or border style when `!workflow.enabled`
2. Consider adding "Disabled" text badge alongside status

**Validation:** List view clearly shows which workflows are disabled.

#### Step 2.5: Export New Components
**Files:** `frontend/src/components/common/index.ts`
**Description:** Export ToggleSwitch component.

**Validation:** Import works from components/common.

---

## Testing Requirements

### Unit Tests
- [ ] `test_toggle_enabled_success()` - Tests successful enable/disable
- [ ] `test_toggle_enabled_not_found()` - Tests 404 for missing workflow
- [ ] `test_toggle_enabled_missing_field()` - Tests 400 for missing `enabled`
- [ ] `test_toggle_cron_workflow_disables_rule()` - EventBridge rule disabled
- [ ] `test_toggle_cron_workflow_enables_rule()` - EventBridge rule enabled
- [ ] `test_toggle_webhook_workflow_no_eventbridge()` - No EventBridge calls for webhook
- [ ] `test_enable_schedule_rule()` - Direct function test
- [ ] `test_disable_schedule_rule()` - Direct function test
- [ ] `test_disable_nonexistent_rule()` - Handles missing rule gracefully

### Integration Tests
- [ ] `test_toggle_via_api()` - Full API flow with DynamoDB mock

### Manual Testing
1. Create cron workflow, verify EventBridge rule is ENABLED in AWS Console
2. Disable workflow via UI, verify EventBridge rule is DISABLED in AWS Console
3. Re-enable workflow via UI, verify EventBridge rule is ENABLED again
4. Create webhook workflow, disable it, send webhook, expect 503 response
5. Disable workflow, verify "Run Now" button is disabled in UI
6. Toggle workflow, verify toast notification appears

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| 404 NotFound | Workflow doesn't exist | Return 404 with message |
| 400 BadRequest | Missing `enabled` field | Return 400 with details |

### Edge Cases
1. **EventBridge rule doesn't exist:** Log warning, don't fail toggle operation
2. **Race condition on toggle:** DynamoDB is atomic, last write wins
3. **Toggle during execution:** Execution continues, only future triggers affected

### Rollback Plan
If toggle feature causes issues:
1. Revert frontend changes (toggle UI)
2. API endpoint can remain (backwards compatible)
3. EventBridge rules remain in their current state

---

## Performance Considerations

- **Expected latency:** <200ms (DynamoDB + EventBridge API)
- **Expected throughput:** Low volume (user toggles manually)
- **Resource limits:** None - no new resources created

---

## Security Considerations

- [x] Input validation implemented (boolean field only)
- [x] No secrets in code
- [x] Least privilege IAM (Lambda already has EventBridge permissions)
- [x] No new attack surface (authenticated API only)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +0 invocations baseline | $0 |
| DynamoDB | +0 WCUs baseline | $0 |
| EventBridge | enable/disable calls | $0 (free tier) |

**Total estimated monthly impact:** $0

---

## Open Questions

1. [x] **Response code for disabled webhook?** → Use 503 Service Unavailable (already implemented in webhook_receiver)
2. [x] **Optimistic update in UI?** → Yes, use React Query optimistic updates for instant feedback
3. [ ] **Should disabled workflows be visually distinct in sidebar nav?** → Defer to PRP-010 follow-up

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are well-defined in INITIAL-011 |
| Feasibility | 10 | All pieces already exist, just need wiring |
| Completeness | 9 | Covers all aspects, minor UI polish decisions can be made during implementation |
| Alignment | 10 | Uses existing patterns, no new services, $0 cost |
| **Overall** | **9.5** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Claude | Initial draft |
