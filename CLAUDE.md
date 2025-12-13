# CLAUDE.md - Automation Platform

> This file provides comprehensive guidance to Claude Code when working on this project.
> Read this file completely at the start of every conversation.

## Project Overview

**Event-Driven Automation Platform** - A personal Zapier/n8n-like system for defining and executing automated workflows. Triggers (webhooks, cron, polling) fire events that flow through user-defined action sequences.

## Critical First Steps

**IMPORTANT: Read and update documentation religiously.**

1. **Always read `docs/PLANNING.md`** at the start of a new conversation to understand architecture, goals, and constraints
2. **Check `docs/TASK.md`** before starting any work - if your task isn't listed, add it with description and date
3. **Review `docs/DECISIONS.md`** for past architecture decisions before proposing alternatives
4. **Check relevant PRPs** in `PRPs/` folder for detailed implementation specs
5. **After completing work**, update TASK.md, commit, and push before ending the session

## Before Starting Any Task

- [ ] Read PLANNING.md for architecture context
- [ ] Check TASK.md - is this task listed? Add if not
- [ ] Check DECISIONS.md - any relevant past decisions?
- [ ] Check PRPs/ - is there a PRP for this?
- [ ] Check examples/ - any patterns to follow?

## After Completing Any Task

- [ ] Update TASK.md with completion status
- [ ] Update DECISIONS.md if you made architecture choices
- [ ] Add/update tests
- [ ] Run linter and fix issues
- [ ] Commit with conventional commit message
- [ ] Push to remote

## Project Constraints

### AWS Budget & Services
- **Monthly budget: ~$20** - Prefer serverless, pay-per-use services
- **Primary services:** Lambda, API Gateway (HTTP API), DynamoDB, Step Functions, EventBridge, SQS, S3, CloudFront
- **Avoid:** RDS, EC2 instances, NAT Gateways, or anything with hourly charges

### Technology Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Infrastructure | AWS CDK | Python |
| Backend | Python | 3.11+ |
| Frontend | React + TypeScript | React 18+ |
| Testing | pytest (backend), Jest (frontend) | Latest |
| Linting | ruff (Python), ESLint (TypeScript) | Latest |

### Code Quality Rules

**IMPORTANT: Never create a file longer than 500 lines of code.** If approaching this limit, refactor into modules.

**File Organization:**
```
lambdas/
  {function_name}/
    handler.py       # Entry point, thin wrapper
    logic.py         # Business logic (if needed)
    models.py        # Pydantic models (if needed)
    requirements.txt # Function-specific deps
```

**Naming Conventions:**
- Files: `snake_case.py`, `kebab-case.tsx`
- Classes: `PascalCase`
- Functions/variables: `snake_case` (Python), `camelCase` (TypeScript)
- Constants: `UPPER_SNAKE_CASE`
- DynamoDB tables: `PascalCase` (Workflows, Executions)
- Lambda functions: `kebab-case` (api-handler, webhook-receiver)

**Import Order (Python):**
```python
# 1. Standard library
import json
import os
from datetime import datetime

# 2. Third-party
import boto3
from pydantic import BaseModel

# 3. Local
from .models import Workflow
from .utils import generate_id
```

## Architecture Patterns

### Lambda Functions
- Use **Powertools for AWS Lambda** for logging, tracing, metrics
- Use **Pydantic** for request/response validation
- Keep handlers thin - delegate to logic functions
- Always include proper error handling with specific exceptions

```python
# Pattern: Lambda handler
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayHttpResolver()

@app.get("/workflows")
@tracer.capture_method
def list_workflows():
    # Implementation
    pass

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    return app.resolve(event, context)
```

### DynamoDB Access
- Use **single-table design** where appropriate
- Always use **Pydantic models** for items
- Use **boto3 resource** (not client) for cleaner code
- Implement pagination for list operations

### Step Functions
- Prefer **Express workflows** for short executions (<5 min)
- Use **intrinsic functions** over Lambda where possible
- Always include error handling with Catch/Retry

### React Frontend
- **Functional components only** - no class components
- Use **React Query** for server state
- Use **Zustand** or **Context** for client state (not Redux)
- Use **React Hook Form** for forms
- Use **Tailwind CSS** for styling

## Testing Requirements

**IMPORTANT: Every new feature must include tests.**

- **Unit tests:** Required for all business logic
- **Integration tests:** Required for Lambda handlers
- **E2E tests:** Required for critical user flows

```bash
# Run tests before committing
cd lambdas && pytest --cov=. --cov-report=term-missing
cd frontend && npm test
```

**Minimum coverage:** 80% for new code

## Documentation Standards

- **Docstrings:** Required for all public functions (Google style)
- **Type hints:** Required for all function signatures
- **Comments:** Explain "why", not "what"
- **README updates:** Required when adding features or changing setup

```python
def create_workflow(name: str, trigger: TriggerConfig, steps: list[StepConfig]) -> Workflow:
    """Create a new workflow with the given configuration.
    
    Args:
        name: Human-readable workflow name
        trigger: Configuration for what initiates the workflow
        steps: Ordered list of actions to execute
        
    Returns:
        The created Workflow object with generated ID
        
    Raises:
        ValidationError: If trigger or steps configuration is invalid
    """
    pass
```

## Git Workflow

**IMPORTANT: Commit and push frequently.**

### When to Commit
After completing ANY of the following, commit and push immediately:
- New feature or functionality
- Bug fix (no matter how small)
- New file or directory structure
- Configuration changes
- Test additions or modifications
- Documentation updates

**Never leave work uncommitted at the end of a session.**

### Branch Naming
- `feature/short-description` - New functionality
- `fix/issue-description` - Bug fixes
- `refactor/what-changed` - Code improvements
- `docs/what-updated` - Documentation only

### Commit Message Format (Conventional Commits)
```
feat: add workflow CRUD API
fix: handle DynamoDB reserved word aliasing
docs: update TASK.md with completed items
refactor: split handler into modules
test: add unit tests for transform action
chore: update dependencies
```

### Documentation Updates Required
**With every code change, update relevant docs:**
- `docs/TASK.md` - Mark tasks in progress or complete
- `docs/DECISIONS.md` - Record any architecture choices made
- `docs/PLANNING.md` - If architecture evolves beyond original plan
- `README.md` - When adding features or changing setup
- Code docstrings - For all new functions/classes

**Never let documentation drift from implementation.**

### PR Requirements
- All tests pass
- No lint errors (ruff, eslint)
- Documentation updated
- Commit messages follow convention

## Environment Setup

```bash
# Python setup (lambdas and CDK)
python -m venv .venv
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
pip install -r requirements-dev.txt

# Frontend setup
cd frontend
npm install

# CDK setup
cd cdk
pip install -r requirements.txt
cdk bootstrap  # first time only
```

## Common Commands

```bash
# Deploy infrastructure
cd cdk && cdk deploy --all

# Run backend tests
cd lambdas && pytest

# Run frontend
cd frontend && npm run dev

# Lint everything
ruff check lambdas/ cdk/
cd frontend && npm run lint

# Synth CDK (check for errors without deploying)
cd cdk && cdk synth
```

## Security Rules

**NEVER:**
- Hardcode credentials or API keys
- Log sensitive data (passwords, tokens, PII)
- Disable SSL verification
- Use `*` in IAM policies for production

**ALWAYS:**
- Use SSM Parameter Store or Secrets Manager for secrets
- Use least-privilege IAM roles
- Validate all user input
- Sanitize data before logging

## Known Gotchas

1. **DynamoDB reserved words:** `name`, `status`, `type` must be aliased in expressions
2. **Lambda cold starts:** Use Powertools for tracing, consider provisioned concurrency for critical paths
3. **Step Functions limits:** Express workflows max 5 min, Standard max 1 year
4. **API Gateway timeout:** 29 seconds max - design for async if longer operations needed
5. **CloudFront cache:** Invalidate after frontend deploys
6. **aws-xray-sdk required for Powertools Tracer:** Must add `aws-xray-sdk>=2.0.0` to Lambda requirements.txt - not included in Lambda runtime by default (see ADR-008)

## Asking Questions

If uncertain about:
- Architecture decisions → Check `docs/DECISIONS.md` first, then ask
- Implementation details → Check examples in `examples/` folder
- Task scope → Check the PRP or ask for clarification

**Never assume. Never hallucinate packages or functions. Verify before using.**
