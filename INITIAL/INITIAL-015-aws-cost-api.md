# INITIAL: AWS Cost API Endpoint

## Goal
Enable a daily Discord notification at 0800 EST showing current month's cumulative AWS cost.

## Why This Approach
AWS Cost Explorer requires SigV4 authentication - can't call directly from HTTP Request action. Adding an internal API endpoint lets us use existing workflow primitives.

## What to Build

### 1. Cost Lambda (`lambdas/cost/`)
- Calls AWS Cost Explorer `GetCostAndUsage` API
- Returns current month's cumulative cost (MTD)
- Response format:
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
    ...
  ]
}
```

### 2. API Route
- `GET /internal/aws-cost` → Cost Lambda
- No auth required (internal use, no sensitive mutation)

### 3. IAM Permission
- Add `ce:GetCostAndUsage` to the Cost Lambda's role

## Files to Modify/Create
- `lambdas/cost/handler.py` - new Lambda
- `lambdas/cost/requirements.txt` - boto3 (if not in layer)
- `cdk/stacks/api_stack.py` - add route + Lambda
- Unit tests for cost Lambda

## Out of Scope
- No new action types
- No frontend changes
- Workflow creation is manual after endpoint works

## Example Workflow (created manually after implementation)
```yaml
name: "Daily AWS Cost Report"
trigger:
  type: cron
  cron_expression: "0 13 * * ? *"  # 0800 EST = 1300 UTC
steps:
  - name: fetch_cost
    type: http_request
    config:
      method: GET
      url: "https://vrcejkbiu4.execute-api.us-east-1.amazonaws.com/internal/aws-cost"
  
  - name: format_message
    type: transform
    config:
      expression: |
        "**AWS Cost Report**\n" +
        "Period: " + steps.fetch_cost.output.body.period.start + " to " + steps.fetch_cost.output.body.period.end + "\n" +
        "**Total: $" + steps.fetch_cost.output.body.total_cost + " " + steps.fetch_cost.output.body.currency + "**"
  
  - name: notify_discord
    type: notify
    config:
      webhook_url: "{{secrets.discord_webhook}}"
      message: "{{steps.format_message.output.result}}"
```

## Success Criteria
1. `GET /internal/aws-cost` returns current month cost data
2. Response includes total and per-service breakdown
3. Can create workflow using this endpoint + existing actions
4. Discord notification arrives at 0800 EST with cost summary

## Estimated Effort
Small - 2-3 hours
