# Examples

> Reference implementations showing project patterns and conventions.
> Copy and adapt these examples for new features.

## Overview

This folder contains example code demonstrating the patterns used throughout the automation platform. When implementing new features, check here first for established conventions.

## Directory Structure

```
examples/
├── README.md           # This file
├── lambda/
│   ├── api_handler.py  # API Gateway Lambda with Powertools
│   └── action.py       # Step Functions action Lambda
└── cdk/
    └── lambda_stack.py # CDK stack for Lambda + API Gateway
```

## Lambda Patterns

### API Handler (`lambda/api_handler.py`)

Use this pattern for Lambda functions that:
- Handle HTTP requests from API Gateway
- Perform CRUD operations
- Need request/response validation

**Key features:**
- AWS Powertools for logging, tracing, and event parsing
- APIGatewayHttpResolver for routing
- Pydantic models for validation
- Proper error handling with HTTP status codes

**When to use:**
- Any endpoint in `api_stack.py`
- REST-style operations (GET, POST, PUT, DELETE)

### Action Lambda (`lambda/action.py`)

Use this pattern for Lambda functions that:
- Execute as Step Functions tasks
- Perform a single action (HTTP request, transform, notify)
- Need to handle step input/output

**Key features:**
- Step Functions task token handling
- Structured input/output for workflow state
- Retry-friendly error handling
- Timeout considerations

**When to use:**
- New action types in `execution_stack.py`
- Step Functions state machine tasks

## CDK Patterns

### Lambda Stack (`cdk/lambda_stack.py`)

Use this pattern for CDK stacks that:
- Create Lambda functions
- Set up API Gateway routes
- Configure DynamoDB access

**Key features:**
- Lambda function with bundled dependencies
- HTTP API with Lambda integration
- Environment variables for configuration
- IAM roles with least privilege

**When to use:**
- Adding new API endpoints
- Creating new Lambda functions
- Setting up infrastructure for new features

## Usage Guidelines

### Copying Examples

1. **Copy, don't reference**: Copy the example file to your target location
2. **Rename appropriately**: Use descriptive names following conventions
3. **Remove unused code**: Don't leave example comments or placeholder logic
4. **Update imports**: Adjust import paths for your location

### Adapting Examples

When adapting an example:

```python
# BEFORE: Example code
@app.get("/example")
def example_handler():
    return {"message": "example"}

# AFTER: Your implementation
@app.get("/workflows")
def list_workflows():
    # Your actual implementation
    return workflows
```

### Common Mistakes to Avoid

1. **Don't hardcode values** - Use environment variables or SSM
2. **Don't skip validation** - Always use Pydantic models
3. **Don't ignore errors** - Handle all expected failure cases
4. **Don't forget logging** - Use logger for debugging
5. **Don't exceed 500 lines** - Split into modules if needed

## Checklist for New Features

Before implementing, verify:

- [ ] Checked `examples/` for relevant patterns
- [ ] Read `CLAUDE.md` for project conventions
- [ ] Reviewed `docs/PLANNING.md` for architecture fit
- [ ] Checked `docs/DECISIONS.md` for relevant ADRs
- [ ] Created or referenced a PRP in `PRPs/`

## Quick Reference

### Powertools Imports
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
```

### Pydantic Model
```python
from pydantic import BaseModel, Field
from datetime import datetime

class MyModel(BaseModel):
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### DynamoDB Access
```python
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

# Get item
response = table.get_item(Key={"pk": "value"})
item = response.get("Item")

# Query
response = table.query(KeyConditionExpression=Key("pk").eq("value"))
items = response.get("Items", [])
```

### Error Response
```python
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, BadRequestError

# Raise to return appropriate HTTP status
raise NotFoundError("Workflow not found")
raise BadRequestError("Invalid workflow configuration")
```
