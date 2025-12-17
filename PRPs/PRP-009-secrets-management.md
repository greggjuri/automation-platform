# PRP-009: Secrets Management UI

> **Status:** Ready
> **Created:** 2025-12-17
> **Author:** Claude
> **Priority:** P1 (High)

---

## Overview

### Problem Statement
Users need to securely store credentials (Discord webhooks, API keys) and reference them in workflows using `{{secrets.name}}` syntax. Currently, secrets must be manually added to SSM Parameter Store via AWS console. There's no way to manage them through the automation platform UI.

### Proposed Solution
Add a Secrets management page (`/secrets`) that allows users to:
- List all secrets (with masked values)
- Create new secrets (stored as SecureString in SSM)
- Delete secrets with confirmation
- See which secret types are supported

Secrets are stored at `/automations/dev/secrets/{name}` in SSM Parameter Store and can be referenced in workflow steps using `{{secrets.name}}`.

### Out of Scope
- Secret rotation or versioning
- External API validation (checking if Discord webhook is valid)
- Multi-environment support (just `dev` for now)
- Secret editing (delete + recreate instead)
- Showing which workflows use a secret

---

## Success Criteria

- [ ] Can navigate to `/secrets` page from main navigation
- [ ] Can view list of existing secrets with name, type, masked value (last 4 chars)
- [ ] Can create a new secret with name, type, and value
- [ ] Can delete a secret with confirmation dialog
- [ ] Secrets are stored as SecureString in SSM at correct path
- [ ] API never exposes full secret values
- [ ] Can use created secret in Notify action as `{{secrets.discord_webhook}}`

**Definition of Done:**
- All success criteria met
- Unit tests for API endpoints (8+ tests)
- Manual testing of create/delete flow
- Documentation updated

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Variable System section mentions `{{secrets.name}}` syntax
- `INITIAL/INITIAL-009-polish-secrets-errors.md` - Original feature request

### Related Code
- `lambdas/api/handler.py` - API Lambda to extend with secrets endpoints
- `lambdas/execution_starter/handler.py` - Already reads secrets from SSM (line ~80)
- `lambdas/shared/interpolation.py` - Already supports `{{secrets.*}}` interpolation
- `cdk/stacks/api_stack.py` - IAM permissions for API Lambda

### Dependencies
- **Requires:** Phase 1-3 complete (API, execution engine, triggers)
- **Blocks:** None (optional enhancement)

### Assumptions
1. Single environment (`dev`) is sufficient for MVP
2. Secret names follow pattern: lowercase, underscores, alphanumeric
3. User understands they should not expose this API publicly without auth

---

## Technical Specification

### Data Models

```python
# Request/Response models for lambdas/api/secrets.py

class SecretCreate(BaseModel):
    """Request body for creating a secret."""
    name: str  # e.g., "discord_webhook"
    value: str  # The actual secret value
    secret_type: str  # "discord_webhook", "slack_webhook", "api_key", "custom"

class SecretMetadata(BaseModel):
    """Secret info returned from list (no actual value)."""
    name: str
    secret_type: str
    masked_value: str  # "****abcd"
    created_at: str  # ISO timestamp from SSM
```

```typescript
// Frontend types in frontend/src/types/secrets.ts

interface Secret {
  name: string;
  secret_type: string;
  masked_value: string;
  created_at: string;
}

interface CreateSecretRequest {
  name: string;
  value: string;
  secret_type: string;
}
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /secrets | List all secrets (metadata only) |
| POST | /secrets | Create new secret |
| DELETE | /secrets/{name} | Delete a secret |

#### GET /secrets Response
```json
{
  "secrets": [
    {
      "name": "discord_webhook",
      "secret_type": "discord_webhook",
      "masked_value": "****abcd",
      "created_at": "2025-12-17T10:00:00Z"
    }
  ],
  "count": 1
}
```

#### POST /secrets Request/Response
```json
// Request
{
  "name": "discord_webhook",
  "value": "https://discord.com/api/webhooks/123/abc",
  "secret_type": "discord_webhook"
}

// Response
{
  "name": "discord_webhook",
  "secret_type": "discord_webhook",
  "masked_value": "****c/abc",
  "created_at": "2025-12-17T10:00:00Z",
  "message": "Secret created successfully"
}
```

#### DELETE /secrets/{name} Response
```json
{
  "message": "Secret 'discord_webhook' deleted",
  "name": "discord_webhook"
}
```

### SSM Storage Pattern

```
/automations/dev/secrets/{name}
  Type: SecureString (KMS encrypted)
  Tags:
    - secret_type: discord_webhook
    - created_by: api
```

### Architecture Diagram
```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Frontend   │────▶│  API Lambda  │────▶│  SSM Parameter  │
│  /secrets   │     │  /secrets/*  │     │     Store       │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Execution   │
                    │   Starter    │
                    │ (reads SSM)  │
                    └──────────────┘
```

---

## Implementation Steps

### Phase 1: Backend API

#### Step 1.1: Add Pydantic Models
**Files:** `lambdas/api/models.py`
**Description:** Add SecretCreate model with validation

```python
class SecretCreate(BaseModel):
    """Request body for creating a secret."""
    name: str = Field(..., pattern=r'^[a-z][a-z0-9_]{0,62}$')
    value: str = Field(..., min_length=1, max_length=4096)
    secret_type: str = Field(..., pattern=r'^(discord_webhook|slack_webhook|api_key|custom)$')
```

**Validation:** Import succeeds, tests pass

#### Step 1.2: Add Secrets Routes to API Lambda
**Files:** `lambdas/api/handler.py`
**Description:** Add GET/POST/DELETE routes for /secrets

```python
@app.get("/secrets")
def list_secrets_handler() -> dict:
    """List all secrets (metadata only)."""
    # Use ssm.get_parameters_by_path() on /automations/dev/secrets/
    pass

@app.post("/secrets")
def create_secret_handler() -> dict:
    """Create a new secret."""
    # Use ssm.put_parameter() with Type='SecureString'
    pass

@app.delete("/secrets/<name>")
def delete_secret_handler(name: str) -> dict:
    """Delete a secret."""
    # Use ssm.delete_parameter()
    pass
```

**Validation:** curl commands work against deployed API

#### Step 1.3: Add IAM Permissions
**Files:** `cdk/stacks/api_stack.py`
**Description:** Grant API Lambda permissions for SSM write/delete

```python
# Add to api_lambda role
api_lambda.add_to_role_policy(iam.PolicyStatement(
    actions=[
        "ssm:GetParametersByPath",
        "ssm:PutParameter",
        "ssm:DeleteParameter",
        "ssm:AddTagsToResource",
    ],
    resources=[
        f"arn:aws:ssm:{region}:{account}:parameter/automations/*/secrets/*"
    ],
))
```

**Validation:** Deploy succeeds, Lambda can call SSM

#### Step 1.4: Unit Tests
**Files:** `lambdas/api/test_secrets.py`
**Description:** Add tests for secrets endpoints

**Validation:** `pytest lambdas/api/test_secrets.py` passes

### Phase 2: Frontend

#### Step 2.1: Add Types and API Client
**Files:** `frontend/src/types/secrets.ts`, `frontend/src/api/secrets.ts`
**Description:** TypeScript types and axios functions

**Validation:** TypeScript compiles without errors

#### Step 2.2: Add React Query Hooks
**Files:** `frontend/src/hooks/useSecrets.ts`
**Description:** Hooks for useSecrets, useCreateSecret, useDeleteSecret

```typescript
export function useSecrets() {
  return useQuery({
    queryKey: ['secrets'],
    queryFn: fetchSecrets,
  });
}

export function useCreateSecret() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSecret,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['secrets'] }),
  });
}
```

**Validation:** Hooks can be imported, TypeScript compiles

#### Step 2.3: Create SecretsPage Component
**Files:** `frontend/src/pages/SecretsPage.tsx`
**Description:** Main page with list, add button, empty state

**Validation:** Page renders at /secrets route

#### Step 2.4: Create AddSecretModal Component
**Files:** `frontend/src/components/secrets/AddSecretModal.tsx`
**Description:** Modal form with type dropdown, name input, value input

**Validation:** Modal opens, form validates, creates secret

#### Step 2.5: Create SecretCard Component
**Files:** `frontend/src/components/secrets/SecretCard.tsx`
**Description:** Card showing secret name, type, masked value, delete button

**Validation:** Cards display correctly in list

#### Step 2.6: Add Delete Confirmation
**Files:** `frontend/src/components/secrets/DeleteSecretModal.tsx`
**Description:** Confirmation dialog before deleting

**Validation:** Delete requires confirmation, secret removed

#### Step 2.7: Add Route and Navigation
**Files:** `frontend/src/App.tsx`, `frontend/src/components/layout/Header.tsx`
**Description:** Add /secrets route and nav link

**Validation:** Can navigate to /secrets from header

### Phase 3: Integration Testing

#### Step 3.1: End-to-End Test
**Description:** Create secret via UI, use in workflow, verify interpolation

1. Create discord_webhook secret with test value
2. Create workflow with Notify action using `{{secrets.discord_webhook}}`
3. Run workflow, verify notify action receives correct URL

**Validation:** Workflow executes successfully with secret value

---

## Testing Requirements

### Unit Tests
- [ ] `test_list_secrets_empty()` - Returns empty list when no secrets
- [ ] `test_list_secrets_with_items()` - Returns metadata, not values
- [ ] `test_create_secret_success()` - Creates SecureString in SSM
- [ ] `test_create_secret_invalid_name()` - Returns 400 for invalid name
- [ ] `test_create_secret_invalid_type()` - Returns 400 for unknown type
- [ ] `test_delete_secret_success()` - Removes from SSM
- [ ] `test_delete_secret_not_found()` - Returns 404
- [ ] `test_mask_value()` - Correctly masks to last 4 chars

### Integration Tests
- [ ] Full CRUD flow via API
- [ ] Secret used in workflow execution

### Manual Testing
1. Navigate to /secrets, see empty state
2. Click "Add Secret", fill form, submit
3. See new secret in list with masked value
4. Delete secret, confirm dialog
5. Secret removed from list

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| 400 Bad Request | Invalid name format | Return validation errors |
| 400 Bad Request | Unknown secret_type | Return valid types |
| 404 Not Found | Delete non-existent secret | Return not found message |
| 409 Conflict | Secret already exists | Return "already exists" error |

### Edge Cases
1. **Secret name with spaces:** Rejected by validation (alphanumeric + underscore only)
2. **Empty value:** Rejected by validation (min_length=1)
3. **Very long value:** Rejected by validation (max_length=4096)
4. **Special characters in value:** Allowed (it's encrypted anyway)
5. **SSM API failure:** Return 500 with generic error message

### Rollback Plan
If deployment fails:
1. Revert CDK changes
2. Existing secrets remain in SSM (not affected)
3. Frontend won't have /secrets route (graceful 404)

---

## Performance Considerations

- **Expected latency:** <500ms for list, <1s for create/delete
- **Expected throughput:** <10 requests/day (personal use)
- **Resource limits:** SSM has 10,000 parameters per account (plenty)

---

## Security Considerations

- [x] API never returns full secret values
- [x] Secrets stored as SecureString (KMS encrypted)
- [x] Masked value shows only last 4 chars
- [x] Delete requires confirmation
- [ ] No authentication on API (existing limitation, not new)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| SSM Parameter Store | +10-20 SecureString params | ~$0.20 |
| Lambda | +50 invocations | ~$0 (free tier) |
| API Gateway | +50 requests | ~$0 (free tier) |

**Total estimated monthly impact:** ~$0.20

---

## Open Questions

1. [x] Should we validate Discord webhook URL format? **Decision:** No, out of scope
2. [x] Should secret names be case-sensitive? **Decision:** No, lowercase only
3. [ ] Should we show "used by" workflows on secret cards? **Decision:** Defer to future

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined scope with clear API contract |
| Feasibility | 9 | Similar patterns exist (execution_starter reads SSM) |
| Completeness | 8 | Missing "used by" but explicitly deferred |
| Alignment | 9 | Matches PLANNING.md variable system |
| **Overall** | **8.75** | |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-17 | Claude | Initial draft from INITIAL-009 |
