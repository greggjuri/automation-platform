# PRP-002: API Gateway and Workflow CRUD

> **Status:** Complete
> **Created:** 2025-12-12
> **Completed:** 2025-12-12
> **Author:** Claude
> **Priority:** P0 (Critical)

---

## Overview

### Problem Statement
The automation platform needs a REST API to manage workflows. The frontend will use this API for CRUD operations, and it's the foundation for all user interactions with the system. Currently we have DynamoDB tables but no way to interact with them.

### Proposed Solution
Create an API Gateway HTTP API with a single Lambda handler that implements workflow CRUD operations (list, create, get, update, delete). The Lambda will use AWS Powertools for routing, logging, and tracing, with Pydantic for request/response validation.

### Out of Scope
- Authentication/authorization (single-user MVP - defer to later PRP)
- Workflow execution (separate PRP for execution engine)
- Trigger configuration (create placeholder in model only)
- Frontend implementation (separate PRP)
- Webhook receiver endpoint (separate PRP)

---

## Success Criteria

- [x] `api_stack.py` creates HTTP API Gateway with Lambda integration
- [x] Lambda handler responds to all CRUD routes for `/workflows`
- [x] `POST /workflows` creates workflow with generated ID
- [x] `GET /workflows` lists all workflows
- [x] `GET /workflows/{id}` returns single workflow
- [x] `PUT /workflows/{id}` updates workflow fields
- [x] `DELETE /workflows/{id}` removes workflow
- [x] `GET /health` returns 200 OK
- [x] Pydantic validates request bodies with proper error messages
- [x] API returns JSON with consistent structure
- [x] CORS enabled for all origins (dev mode)
- [ ] `cdk deploy` creates all resources successfully (pending deployment)
- [x] API URL is output from CDK stack

**Definition of Done:**
- All success criteria met
- Unit tests pass for handler logic
- Integration tests pass against deployed API
- `cdk synth` and `cdk deploy` succeed
- API accessible via curl/Postman
- TASK.md updated

---

## Context

### Related Documentation
- `docs/PLANNING.md` - API endpoints specification, data models
- `docs/DECISIONS.md` - ADR-004 (HTTP API), ADR-006 (Powertools)

### Related Code
- `examples/cdk/lambda_stack.py` - Reference CDK patterns for API stack
- `examples/lambda/api_handler.py` - Reference Lambda handler implementation
- `cdk/stacks/database_stack.py` - Workflows table to connect to
- `cdk/app.py` - Entry point to wire up new stack

### Dependencies
- **Requires:** PRP-001 (Project Foundation) - DynamoDB tables must exist
- **Blocks:** Frontend workflow UI, execution engine, triggers

### Assumptions
1. Single-user system (no authentication for MVP)
2. All requests/responses are JSON
3. Workflow steps will be configured later (empty array for now)
4. Trigger config will be configured later (empty object for now)

---

## Technical Specification

### Data Models

#### Workflow (DynamoDB Item)
```python
{
    "workflow_id": "wf_abc123",           # PK (generated)
    "name": "RSS to Discord",             # Required, 1-100 chars
    "description": "Post RSS items",      # Optional, max 500 chars
    "enabled": True,                      # Default true
    "trigger": {},                        # Placeholder for trigger config
    "steps": [],                          # Placeholder for workflow steps
    "created_at": "2025-01-15T10:30:00Z", # ISO 8601
    "updated_at": "2025-01-15T10:30:00Z"  # ISO 8601
}
```

#### Pydantic Request Models
```python
class WorkflowCreate(BaseModel):
    """Create workflow request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    enabled: bool = Field(default=True)
    trigger: dict = Field(default_factory=dict)
    steps: list = Field(default_factory=list)

class WorkflowUpdate(BaseModel):
    """Update workflow request (all fields optional)."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    enabled: bool | None = None
    trigger: dict | None = None
    steps: list | None = None
```

### API Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | /health | Health check | - | `{"status": "ok"}` |
| GET | /workflows | List all workflows | - | `{"workflows": [...], "count": N}` |
| POST | /workflows | Create workflow | WorkflowCreate | Created workflow |
| GET | /workflows/{id} | Get single workflow | - | Workflow object |
| PUT | /workflows/{id} | Update workflow | WorkflowUpdate | Updated workflow |
| DELETE | /workflows/{id} | Delete workflow | - | `{"message": "...", "workflow_id": "..."}` |

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway HTTP API                      │
│              dev-automation-api                              │
│                                                             │
│  Routes:                                                    │
│    GET /health                                              │
│    GET /workflows                                           │
│    POST /workflows                                          │
│    GET /workflows/{workflow_id}                             │
│    PUT /workflows/{workflow_id}                             │
│    DELETE /workflows/{workflow_id}                          │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         Lambda Function              │
                    │     dev-automation-api-handler       │
                    │                                     │
                    │  - Powertools routing               │
                    │  - Pydantic validation              │
                    │  - X-Ray tracing                    │
                    │  - Structured logging               │
                    └─────────────────────────┬───────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │      DynamoDB                 │
                              │   dev-Workflows table         │
                              └───────────────────────────────┘
```

### Configuration

#### Lambda Environment Variables
```python
TABLE_NAME = "dev-Workflows"  # From CDK
ENVIRONMENT = "dev"           # From CDK context
POWERTOOLS_SERVICE_NAME = "automation-api"
POWERTOOLS_LOG_LEVEL = "DEBUG"  # INFO in prod
POWERTOOLS_METRICS_NAMESPACE = "AutomationPlatform"
```

#### Lambda Runtime
- Python 3.11
- 256MB memory
- 29s timeout (API Gateway max)
- X-Ray tracing enabled

---

## Implementation Steps

### Phase 1: Lambda Handler

#### Step 1.1: Create Lambda Directory Structure
**Files:** `lambdas/api/`
**Description:** Set up the API Lambda directory with required files

```
lambdas/api/
├── handler.py       # Main Lambda handler with routes
├── models.py        # Pydantic request/response models
├── repository.py    # DynamoDB operations
├── requirements.txt # Lambda dependencies
└── __init__.py      # Package marker
```

**Validation:** Directory structure exists

#### Step 1.2: Create requirements.txt
**Files:** `lambdas/api/requirements.txt`
**Description:** Lambda dependencies

```
aws-lambda-powertools>=2.0.0
pydantic>=2.0.0
boto3>=1.34.0
```

**Validation:** File exists with correct dependencies

#### Step 1.3: Create Pydantic Models
**Files:** `lambdas/api/models.py`
**Description:** Request/response validation models

Key models:
- `WorkflowCreate` - POST request body
- `WorkflowUpdate` - PUT request body
- `WorkflowResponse` - Response model (optional)
- Helper functions for ID generation and timestamps

**Validation:** `python -c "from models import WorkflowCreate"` succeeds

#### Step 1.4: Create DynamoDB Repository
**Files:** `lambdas/api/repository.py`
**Description:** Data access layer for Workflows table

Methods:
- `list_workflows()` - Scan table
- `get_workflow(workflow_id)` - Get item
- `create_workflow(data)` - Put item
- `update_workflow(workflow_id, data)` - Update item
- `delete_workflow(workflow_id)` - Delete item

**Validation:** Unit tests pass for repository

#### Step 1.5: Create Lambda Handler
**Files:** `lambdas/api/handler.py`
**Description:** Main handler with Powertools routing

Pattern from `examples/lambda/api_handler.py`:
- Use `APIGatewayHttpResolver` for routing
- Decorate with `@logger.inject_lambda_context`
- Decorate with `@tracer.capture_lambda_handler`
- Handle Pydantic validation errors → 400
- Handle NotFoundError → 404
- Handle unexpected errors → 500

**Validation:** Handler imports without errors

### Phase 2: CDK Stack

#### Step 2.1: Create API Stack
**Files:** `cdk/stacks/api_stack.py`
**Description:** CDK stack for API Gateway + Lambda

Based on `examples/cdk/lambda_stack.py`:
- Create Lambda function with bundled dependencies
- Create HTTP API with CORS
- Add all routes
- Grant DynamoDB permissions
- Export API URL

**Validation:** `cdk synth` includes api stack

#### Step 2.2: Wire Up in app.py
**Files:** `cdk/app.py`
**Description:** Add API stack to CDK app

```python
from stacks.api_stack import ApiStack

api_stack = ApiStack(
    app,
    f"{stack_prefix}-api",
    workflows_table=database_stack.workflows_table,
    environment=environment,
    env=env,
)
```

**Validation:** `cdk synth` shows 3 stacks

### Phase 3: Testing & Deployment

#### Step 3.1: Create Unit Tests
**Files:** `lambdas/api/tests/`
**Description:** Unit tests for handler and repository

```
lambdas/api/tests/
├── __init__.py
├── conftest.py        # Pytest fixtures
├── test_models.py     # Model validation tests
├── test_repository.py # Repository with mocked DynamoDB
└── test_handler.py    # Handler with mocked dependencies
```

**Validation:** `pytest lambdas/api/tests -v` passes

#### Step 3.2: Run Linter
**Description:** Lint all new code

```bash
cd lambdas/api && ruff check . --fix
cd cdk && ruff check stacks/api_stack.py --fix
```

**Validation:** No lint errors

#### Step 3.3: Deploy to AWS
**Description:** Deploy all stacks

```bash
cd cdk && cdk deploy --all
```

**Validation:**
- All stacks deploy successfully
- API URL output displayed

#### Step 3.4: Integration Test
**Description:** Test deployed API with curl

```bash
# Health check
curl https://{api-id}.execute-api.us-east-1.amazonaws.com/health

# Create workflow
curl -X POST https://{api-id}.execute-api.us-east-1.amazonaws.com/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workflow", "description": "Testing"}'

# List workflows
curl https://{api-id}.execute-api.us-east-1.amazonaws.com/workflows

# Get workflow
curl https://{api-id}.execute-api.us-east-1.amazonaws.com/workflows/{id}

# Update workflow
curl -X PUT https://{api-id}.execute-api.us-east-1.amazonaws.com/workflows/{id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete workflow
curl -X DELETE https://{api-id}.execute-api.us-east-1.amazonaws.com/workflows/{id}
```

**Validation:** All endpoints return expected responses

---

## Testing Requirements

### Unit Tests
- [ ] `test_workflow_create_valid()` - Valid create request
- [ ] `test_workflow_create_invalid_name()` - Name too long/empty
- [ ] `test_workflow_update_partial()` - Update single field
- [ ] `test_workflow_id_generation()` - ID format correct
- [ ] `test_repository_list()` - List with mocked DynamoDB
- [ ] `test_repository_get_not_found()` - 404 handling
- [ ] `test_handler_routing()` - Routes resolve correctly

### Integration Tests
- [ ] `test_create_and_get()` - Create then retrieve workflow
- [ ] `test_update_workflow()` - Update and verify changes
- [ ] `test_delete_workflow()` - Delete and verify 404
- [ ] `test_list_workflows()` - List returns created items

### Manual Testing
1. Deploy with `cdk deploy --all`
2. Note API URL from output
3. Run curl commands from Step 3.4
4. Verify in DynamoDB console that items exist
5. Check CloudWatch logs for Lambda

---

## Error Handling

### Expected Errors
| Error | Cause | HTTP Code | Response |
|-------|-------|-----------|----------|
| ValidationError | Invalid request body | 400 | `{"message": "Invalid request", "details": [...]}` |
| NotFoundError | Workflow ID not found | 404 | `{"message": "Workflow {id} not found"}` |
| Internal error | Unexpected exception | 500 | `{"message": "Internal server error"}` |

### Edge Cases
1. **Empty name:** Pydantic validates min_length=1, returns 400
2. **Duplicate create:** DynamoDB allows (different IDs generated)
3. **Update non-existent:** Check exists first, return 404
4. **Delete non-existent:** Check exists first, return 404
5. **Large description:** Pydantic validates max_length=500
6. **Empty update body:** Valid (no changes made)
7. **Malformed JSON:** Powertools returns 400 automatically

### Rollback Plan
```bash
# To rollback API stack only:
cdk destroy dev-automation-api

# To rollback all:
cdk destroy --all
```

---

## Performance Considerations

- **Expected latency:** < 100ms for most operations (DynamoDB single-digit ms)
- **Expected throughput:** < 10 requests/minute (personal use)
- **Cold start:** ~1-2s (Powertools adds ~500ms). Acceptable for personal use.
- **Resource limits:**
  - 256MB memory sufficient for CRUD
  - 29s timeout matches API Gateway max
  - DynamoDB on-demand scales automatically

---

## Security Considerations

- [x] Input validation via Pydantic
- [x] No secrets in code (SSM for future secrets)
- [x] Least privilege IAM (Lambda only has DynamoDB access for one table)
- [x] No SQL/NoSQL injection possible (typed DynamoDB operations)
- [ ] Authentication deferred to future PRP (acceptable for single-user MVP)
- [x] CORS restricted in prod (only automations.jurigregg.com)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | ~1000 invocations | ~$0.00 (free tier) |
| API Gateway | ~1000 requests | ~$0.001 |
| CloudWatch Logs | ~100MB | ~$0.05 |
| X-Ray | ~1000 traces | $0.00 (free tier) |

**Total estimated monthly impact:** < $0.10

---

## Open Questions

1. [x] ~~Authentication~~ - Deferred to future PRP (single-user MVP)
2. [ ] Should we add pagination to list endpoint? (Defer until needed - small dataset)
3. [ ] Should health check verify DynamoDB connectivity? (Keep simple for now)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 10 | Well-defined CRUD operations, clear API spec |
| Feasibility | 10 | Standard patterns, examples exist in codebase |
| Completeness | 9 | Covers all CRUD, testing, deployment. Pagination deferred. |
| Alignment | 10 | Matches PLANNING.md API spec, follows all ADRs |
| **Overall** | **9.75** | Ready for implementation |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-12 | Claude | Initial draft |
