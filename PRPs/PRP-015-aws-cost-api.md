# PRP-015: AWS Cost API Endpoint

> **Status:** Complete
> **Created:** 2025-12-26
> **Author:** Claude
> **Priority:** P2 (Medium)

---

## Overview

### Problem Statement
The platform needs to display current month AWS costs via Discord notifications at 0800 EST daily. AWS Cost Explorer requires SigV4 authentication, making it impossible to call directly from the existing HTTP Request action. An internal API endpoint is needed to proxy Cost Explorer data.

### Proposed Solution
Create a new Lambda function and API endpoint (`GET /internal/aws-cost`) that:
1. Calls AWS Cost Explorer `GetCostAndUsage` API
2. Returns month-to-date costs with per-service breakdown
3. Requires no authentication (internal use only, read-only)

This enables workflows to fetch cost data using the existing HTTP Request action, then format and send via Discord notify action.

### Out of Scope
- No new action types
- No frontend changes
- No authentication for the endpoint (internal use only)
- Workflow creation (done manually after endpoint works)

---

## Success Criteria

- [ ] `GET /internal/aws-cost` returns current month cost data
- [ ] Response includes period (start/end dates), total cost, and per-service breakdown
- [ ] Costs displayed in USD with 2 decimal precision
- [ ] Unit tests with >80% coverage
- [ ] Can create workflow using this endpoint + existing actions
- [ ] Discord notification arrives with cost summary (manual verification)

**Definition of Done:**
- All success criteria met
- Tests written and passing
- Code reviewed
- Documentation updated
- Deployed to dev/staging

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, API Gateway patterns
- `docs/DECISIONS.md` - ADR-004 (HTTP API), ADR-006 (Powertools)
- `INITIAL/INITIAL-015-aws-cost-api.md` - Original requirements

### Related Code
- `lambdas/api/handler.py` - Existing API handler pattern (Powertools resolver)
- `cdk/stacks/api_stack.py` - How to add routes and Lambdas
- `lambdas/webhook_receiver/` - Example of standalone Lambda with minimal deps

### Dependencies
- **Requires:** None (standalone feature)
- **Blocks:** Daily AWS Cost Report workflow (created manually after implementation)

### Assumptions
1. AWS Cost Explorer is enabled in the account (it is enabled by default for accounts with billing access)
2. The Lambda execution role can be granted `ce:GetCostAndUsage` permission
3. Cost Explorer data is available with ~24 hour delay (current day partial)
4. No need for historical cost queries (MTD only)

---

## Technical Specification

### Data Models

```python
from pydantic import BaseModel
from datetime import date

class ServiceCost(BaseModel):
    """Cost breakdown for a single AWS service."""
    name: str
    cost: str  # String with 2 decimal places, e.g., "3.45"

class CostResponse(BaseModel):
    """Response from the AWS cost endpoint."""
    period: dict  # {"start": "2024-12-01", "end": "2024-12-25"}
    total_cost: str  # String with 2 decimal places, e.g., "14.23"
    currency: str  # "USD"
    services: list[ServiceCost]  # Sorted by cost descending
```

### API Changes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /internal/aws-cost | Get current month AWS cost summary |

### Response Format

```json
{
  "period": {
    "start": "2024-12-01",
    "end": "2024-12-25"
  },
  "total_cost": "14.23",
  "currency": "USD",
  "services": [
    {"name": "Amazon DynamoDB", "cost": "3.45"},
    {"name": "AWS Lambda", "cost": "2.10"},
    {"name": "Amazon API Gateway", "cost": "1.50"},
    {"name": "Amazon CloudFront", "cost": "0.85"}
  ]
}
```

### Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  API Gateway    │────▶│  Cost Lambda     │────▶│ AWS Cost Explorer │
│  GET /internal/ │     │  (new function)  │     │ GetCostAndUsage   │
│   aws-cost      │     │                  │     │                   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

### Configuration

```python
# Environment variables (set by CDK)
ENVIRONMENT = "dev"  # For logging context
POWERTOOLS_SERVICE_NAME = "cost-api"
POWERTOOLS_LOG_LEVEL = "DEBUG"  # or "INFO" in prod
```

---

## Implementation Steps

### Phase 1: Lambda Function

#### Step 1.1: Create Cost Lambda Directory
**Files:** `lambdas/cost/`
**Description:** Create new Lambda directory with required files

```
lambdas/cost/
├── handler.py       # Main handler
├── requirements.txt # Dependencies
└── __init__.py     # Empty init file
```

**Validation:** Directory structure exists

#### Step 1.2: Implement Cost Lambda Handler
**Files:** `lambdas/cost/handler.py`
**Description:** Implement handler that calls Cost Explorer and returns formatted response

```python
from datetime import date, timedelta
import boto3
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
ce_client = boto3.client("ce")

@tracer.capture_method
def get_month_to_date_costs() -> dict:
    """Get MTD costs from Cost Explorer."""
    today = date.today()
    start_of_month = today.replace(day=1)
    # Cost Explorer End date is EXCLUSIVE, so add 1 day to include today
    end_date = today + timedelta(days=1)

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_of_month.isoformat(),
            "End": end_date.isoformat(),  # Exclusive: "2024-12-26" includes through Dec 25
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    # Parse and format response
    ...
```

**Validation:** Lambda can be invoked locally with SAM or tested via unit tests

#### Step 1.3: Create requirements.txt
**Files:** `lambdas/cost/requirements.txt`
**Description:** Minimal dependencies (boto3 is in runtime, but Powertools needs explicit deps)

```
aws-lambda-powertools>=2.0.0
aws-xray-sdk>=2.0.0
```

**Validation:** `pip install -r requirements.txt` succeeds

### Phase 2: CDK Stack Updates

#### Step 2.1: Add Cost Lambda to API Stack
**Files:** `cdk/stacks/api_stack.py`
**Description:** Create new Lambda function with ce:GetCostAndUsage permission

Key additions:
1. Create log group for cost Lambda
2. Create Lambda function with bundling
3. Add IAM policy for `ce:GetCostAndUsage`
4. Create integration and route

```python
def _create_cost_lambda(self) -> None:
    """Create the Cost API Lambda function."""
    # Log group
    log_group = logs.LogGroup(...)

    # Lambda function
    self.cost_handler = lambda_.Function(
        self,
        "CostHandler",
        function_name=f"{self.env_name}-automation-cost-handler",
        ...
    )

    # IAM permission for Cost Explorer
    self.cost_handler.add_to_role_policy(
        iam.PolicyStatement(
            actions=["ce:GetCostAndUsage"],
            resources=["*"],  # Cost Explorer doesn't support resource-level permissions
        )
    )
```

**Validation:** `cdk synth` succeeds with no errors

#### Step 2.2: Add API Route
**Files:** `cdk/stacks/api_stack.py`
**Description:** Add route for GET /internal/aws-cost

```python
# Cost API route
cost_integration = integrations.HttpLambdaIntegration(
    "CostIntegration",
    handler=self.cost_handler,
)

self.api.add_routes(
    path="/internal/aws-cost",
    methods=[apigwv2.HttpMethod.GET],
    integration=cost_integration,
)
```

**Validation:** Route appears in `cdk synth` output

### Phase 3: Testing

#### Step 3.1: Unit Tests for Cost Lambda
**Files:** `lambdas/cost/tests/test_handler.py`
**Description:** Test cost parsing, date handling, error cases

Key test cases:
1. Successful cost retrieval with multiple services
2. Empty services list (new account or no usage)
3. Cost Explorer API error handling
4. Date calculation for month boundaries
5. Decimal formatting (2 decimal places)

**Validation:** `pytest lambdas/cost/tests/ -v` passes

### Phase 4: Deployment and Verification

#### Step 4.1: Deploy to AWS
**Files:** None (CDK command)
**Description:** Deploy updated stacks

```bash
cd cdk && cdk deploy --all
```

**Validation:** Deployment succeeds, new Lambda visible in AWS Console

#### Step 4.2: Test Endpoint
**Files:** None (manual test)
**Description:** Call endpoint and verify response

```bash
curl https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com/internal/aws-cost
```

**Validation:** Response matches expected format with actual costs

---

## Testing Requirements

### Unit Tests
- [ ] `test_get_costs_success()` - Tests successful cost retrieval with mocked CE response
- [ ] `test_get_costs_no_services()` - Tests empty services list handling
- [ ] `test_get_costs_api_error()` - Tests Cost Explorer API error handling
- [ ] `test_date_calculation_start_of_month()` - Tests period calculation on day 1
- [ ] `test_date_calculation_mid_month()` - Tests period calculation mid-month
- [ ] `test_end_date_exclusive()` - Tests End date is today+1 (CE uses exclusive end)
- [ ] `test_cost_formatting()` - Tests decimal formatting to 2 places
- [ ] `test_services_sorted_by_cost()` - Tests services sorted descending by cost

### Integration Tests
- [ ] `test_lambda_handler()` - Tests full handler with mocked boto3

### Manual Testing
1. Deploy to AWS
2. Call `/internal/aws-cost` endpoint
3. Verify response format matches specification
4. Verify costs are accurate (compare to AWS Console Cost Explorer)
5. Create test workflow: HTTP Request → Transform → Log
6. Verify workflow executes successfully

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| AccessDeniedException | Missing ce:GetCostAndUsage permission | Return 500 with error message |
| Cost Explorer not enabled | Account setting | Return 500 with helpful message |
| Rate limit exceeded | Too many API calls | Return 429, log for investigation |

### Edge Cases
1. **First day of month:** Start and end dates are the same - CE handles this correctly
2. **No cost data yet:** New account or no usage - return empty services list with $0.00 total
3. **Very large number of services:** Limit to top 20 services by cost, group rest as "Other"

### Rollback Plan
1. If deployment fails: `cdk deploy --rollback`
2. If Lambda errors in production: Update route to return static fallback or disable workflow

---

## Performance Considerations

- **Expected latency:** 500-1500ms (Cost Explorer API is slow)
- **Expected throughput:** 1-2 requests/day (cron workflow only)
- **Resource limits:**
  - Memory: 128MB sufficient
  - Timeout: 10 seconds (CE API can be slow)
- **Caching:** Not implemented (daily refresh is fine)

---

## Security Considerations

- [x] Input validation implemented (no user input, just date calculations)
- [x] No secrets in code
- [x] Least privilege IAM (only ce:GetCostAndUsage)
- [ ] Endpoint uses /internal/ prefix to signal internal use
- [ ] No authentication required (read-only cost data, not sensitive)

Note: The `/internal/` prefix is a convention only. If protecting this data is important in the future, add API Gateway authorization.

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| Lambda | +1 function, ~30 invocations/month | ~$0.00 (free tier) |
| Cost Explorer | +30 API calls/month | ~$0.01 (first 10 free) |
| CloudWatch Logs | +1 log group | ~$0.01 |

**Total estimated monthly impact:** <$0.05

---

## Open Questions

1. [x] Should the endpoint be protected? → No, read-only cost data is not sensitive
2. [x] Should we cache results? → No, daily refresh is sufficient and adds complexity
3. [ ] Top N services or all services? → Start with all, can limit later if response too large

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Requirements are clear and well-defined in INITIAL file |
| Feasibility | 9 | Standard Lambda + API pattern, Cost Explorer API is straightforward |
| Completeness | 8 | Covers all aspects, minor details like "Other" grouping TBD |
| Alignment | 10 | Fits existing patterns perfectly, minimal cost, no conflicts |
| **Overall** | **9.0** | High confidence - straightforward implementation |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-26 | Claude | Initial draft |
