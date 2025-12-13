# PRP-001: Project Foundation & CDK Setup

> **Status:** Complete
> **Created:** 2025-12-12
> **Author:** Claude
> **Priority:** P0 (Critical)

---

## Overview

### Problem Statement
The automation platform needs foundational AWS infrastructure before any features can be built. Currently, the project has only scaffolding (docs, examples) but no actual CDK code, DynamoDB tables, or project structure for lambdas and frontend.

### Proposed Solution
Initialize the complete AWS CDK project with Python, create all required DynamoDB tables (Workflows, Executions, PollState), set up SSM parameter paths for configuration/secrets, and establish the directory structure for lambdas and React frontend.

### Out of Scope
- Lambda function implementations (separate PRPs)
- API Gateway setup (PRP-002)
- Frontend implementation beyond Vite initialization
- CI/CD pipeline
- Custom domain setup

---

## Success Criteria

- [ ] CDK project initialized at `cdk/` with Python virtual environment
- [ ] `cdk synth` runs without errors
- [ ] DynamoDB `Workflows` table created with `workflow_id` as partition key
- [ ] DynamoDB `Executions` table created with composite key (`workflow_id`, `execution_id`) and GSI
- [ ] DynamoDB `PollState` table created with `workflow_id` as partition key
- [ ] SSM parameter paths created for `/automations/config/` and `/automations/secrets/`
- [ ] `cdk deploy` succeeds and creates resources in AWS
- [ ] Lambda directory structure created at `lambdas/`
- [ ] Frontend initialized with Vite + React + TypeScript at `frontend/`
- [ ] All tables use on-demand capacity (PAY_PER_REQUEST)
- [ ] Executions table has TTL enabled for automatic cleanup

**Definition of Done:**
- All success criteria met
- `cdk synth` produces valid CloudFormation
- `cdk deploy` creates all resources
- Tables visible in AWS Console
- Documentation updated (TASK.md marked complete)

---

## Context

### Related Documentation
- `docs/PLANNING.md` - Architecture overview, data models, CDK stack organization
- `docs/DECISIONS.md` - ADR-001 (CDK Python), ADR-002 (DynamoDB), ADR-005 (React TypeScript)

### Related Code
- `examples/cdk/lambda_stack.py` - Reference patterns for CDK constructs
- `examples/lambda/api_handler.py` - Reference for Lambda patterns

### Dependencies
- **Requires:** AWS account configured, AWS CLI credentials
- **Blocks:** All other Phase 1 tasks (API stack, Lambda implementations, frontend)

### Assumptions
1. AWS CLI is configured with appropriate credentials
2. CDK has been bootstrapped in the target account/region (`cdk bootstrap`)
3. Python 3.11+ is installed
4. Node.js 18+ is installed (for frontend and CDK)

---

## Technical Specification

### Data Models

#### Workflows Table

```python
# Primary Key: workflow_id (String)
# No Sort Key (simple key design)

{
    "workflow_id": "wf_abc123",        # PK
    "name": "RSS to Discord",
    "description": "Post new RSS items to Discord",
    "enabled": True,
    "trigger": {
        "type": "poll",
        "config": {...}
    },
    "steps": [...],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

#### Executions Table

```python
# Primary Key: workflow_id (String) + execution_id (String)
# GSI: status-started_at-index (status PK, started_at SK)
# TTL: ttl attribute (epoch seconds, 90 days from creation)

{
    "workflow_id": "wf_abc123",        # PK
    "execution_id": "ex_01HQ...",      # SK (ULID for sortability)
    "status": "success",               # pending | running | success | failed
    "trigger_data": {...},
    "steps": [...],
    "started_at": "2025-01-15T10:45:00Z",
    "finished_at": "2025-01-15T10:45:01Z",
    "error": None,
    "ttl": 1713168000                  # Auto-delete after 90 days
}
```

#### PollState Table

```python
# Primary Key: workflow_id (String)

{
    "workflow_id": "wf_abc123",        # PK
    "last_checked_at": "2025-01-15T10:30:00Z",
    "last_content_hash": "abc123...",
    "seen_item_ids": ["item1", "item2"],
    "last_error": None
}
```

### Directory Structure After Implementation

```
automation-platform/
├── cdk/
│   ├── app.py                    # CDK entry point
│   ├── cdk.json                  # CDK configuration
│   ├── requirements.txt          # CDK dependencies
│   └── stacks/
│       ├── __init__.py
│       ├── shared_stack.py       # IAM roles, SSM paths
│       └── database_stack.py     # DynamoDB tables
├── lambdas/
│   ├── api/                      # API handler (future)
│   │   └── .gitkeep
│   └── actions/                  # Action handlers (future)
│       └── .gitkeep
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       └── vite-env.d.ts
└── ...existing files
```

### SSM Parameter Structure

```
/automations/
├── config/
│   ├── environment          # dev | staging | prod
│   └── log_level           # DEBUG | INFO | WARN
└── secrets/
    ├── discord_webhook     # Discord webhook URL
    └── api_keys/           # External API keys
        └── {service_name}
```

---

## Implementation Steps

### Phase 1: CDK Project Setup

#### Step 1.1: Create CDK Directory Structure
**Files:** `cdk/`, `cdk/stacks/`
**Description:** Create the CDK project directory and stacks subdirectory

```bash
mkdir -p cdk/stacks
touch cdk/stacks/__init__.py
```

**Validation:** Directories exist

#### Step 1.2: Create CDK Configuration Files
**Files:** `cdk/cdk.json`
**Description:** CDK configuration with context for environment

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "source.bat",
      "**/__pycache__",
      "**/.pytest_cache",
      "**/*.pyc",
      ".venv"
    ]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": ["aws"],
    "environment": "dev"
  }
}
```

**Validation:** File exists and is valid JSON

#### Step 1.3: Create CDK Requirements
**Files:** `cdk/requirements.txt`
**Description:** Python dependencies for CDK project

```
aws-cdk-lib>=2.170.0
constructs>=10.0.0
```

**Validation:** File exists

#### Step 1.4: Create CDK App Entry Point
**Files:** `cdk/app.py`
**Description:** Main CDK application that wires together all stacks

```python
#!/usr/bin/env python3
"""CDK Application entry point for Automation Platform.

This app creates all infrastructure stacks for the automation platform.
Deploy order: shared → database → (api, triggers, execution) → frontend
"""

import os

import aws_cdk as cdk

from stacks.database_stack import DatabaseStack
from stacks.shared_stack import SharedStack

# Get environment from context or default
app = cdk.App()
environment = app.node.try_get_context("environment") or "dev"

# AWS environment configuration
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

# Stack naming convention: {env}-automation-{stack}
stack_prefix = f"{environment}-automation"

# Shared resources (IAM, SSM paths)
shared_stack = SharedStack(
    app,
    f"{stack_prefix}-shared",
    environment=environment,
    env=env,
)

# Database tables
database_stack = DatabaseStack(
    app,
    f"{stack_prefix}-database",
    environment=environment,
    env=env,
)

# Add tags to all resources
cdk.Tags.of(app).add("Project", "AutomationPlatform")
cdk.Tags.of(app).add("Environment", environment)
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
```

**Validation:** `python3 cdk/app.py` runs without import errors

### Phase 2: Shared Stack

#### Step 2.1: Create Shared Stack
**Files:** `cdk/stacks/shared_stack.py`
**Description:** IAM roles and SSM parameter paths

```python
"""Shared resources stack for Automation Platform.

Creates:
- SSM Parameter Store paths for configuration and secrets
- Base IAM policies for Lambda functions
"""

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class SharedStack(Stack):
    """Stack for shared resources used by multiple components.

    Attributes:
        config_path: SSM path prefix for configuration parameters
        secrets_path: SSM path prefix for secret parameters
        lambda_base_role: Base IAM role for Lambda functions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize shared stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment

        # SSM parameter path prefixes
        self.config_path = f"/automations/{environment}/config"
        self.secrets_path = f"/automations/{environment}/secrets"

        # Create base configuration parameters
        self._create_config_parameters()

        # Create base IAM role for Lambda functions
        self._create_lambda_base_role()

    def _create_config_parameters(self) -> None:
        """Create base configuration parameters in SSM."""

        # Environment parameter
        ssm.StringParameter(
            self,
            "EnvironmentParam",
            parameter_name=f"{self.config_path}/environment",
            string_value=self.environment,
            description="Deployment environment",
            tier=ssm.ParameterTier.STANDARD,
        )

        # Log level parameter
        log_level = "DEBUG" if self.environment == "dev" else "INFO"
        ssm.StringParameter(
            self,
            "LogLevelParam",
            parameter_name=f"{self.config_path}/log_level",
            string_value=log_level,
            description="Default log level for Lambda functions",
            tier=ssm.ParameterTier.STANDARD,
        )

    def _create_lambda_base_role(self) -> None:
        """Create base IAM role that Lambda functions can assume."""

        self.lambda_base_role = iam.Role(
            self,
            "LambdaBaseRole",
            role_name=f"{self.environment}-automation-lambda-base",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Base role for automation platform Lambda functions",
            managed_policies=[
                # Basic Lambda execution
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                # X-Ray tracing
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSXRayDaemonWriteAccess"
                ),
            ],
        )

        # Allow reading config parameters
        self.lambda_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadConfigParameters",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{self.config_path}/*",
                ],
            )
        )

        # Allow reading secrets (with decrypt)
        self.lambda_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadSecretParameters",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{self.secrets_path}/*",
                ],
            )
        )
```

**Validation:** Stack synths without errors, creates SSM parameters and IAM role

### Phase 3: Database Stack

#### Step 3.1: Create Database Stack
**Files:** `cdk/stacks/database_stack.py`
**Description:** DynamoDB tables for workflows, executions, and poll state

```python
"""Database stack for Automation Platform.

Creates DynamoDB tables:
- Workflows: Store workflow definitions
- Executions: Store workflow execution history (with TTL)
- PollState: Track polling trigger state
"""

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class DatabaseStack(Stack):
    """Stack for DynamoDB tables.

    Attributes:
        workflows_table: Table for workflow definitions
        executions_table: Table for execution history
        poll_state_table: Table for polling trigger state
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize database stack.

        Args:
            scope: CDK scope
            construct_id: Stack identifier
            environment: Deployment environment
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        self.environment = environment

        # Set removal policy based on environment
        removal_policy = (
            RemovalPolicy.DESTROY if environment == "dev"
            else RemovalPolicy.RETAIN
        )

        # Create tables
        self._create_workflows_table(removal_policy)
        self._create_executions_table(removal_policy)
        self._create_poll_state_table(removal_policy)

    def _create_workflows_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the Workflows table.

        Schema:
        - PK: workflow_id (String)
        """
        self.workflows_table = dynamodb.Table(
            self,
            "WorkflowsTable",
            table_name=f"{self.environment}-Workflows",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            # Stream for future event-driven features
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

    def _create_executions_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the Executions table.

        Schema:
        - PK: workflow_id (String)
        - SK: execution_id (String, ULID for time-based sorting)
        - GSI: status-started_at-index for querying by status
        - TTL: ttl attribute for automatic cleanup after 90 days
        """
        self.executions_table = dynamodb.Table(
            self,
            "ExecutionsTable",
            table_name=f"{self.environment}-Executions",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="execution_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            # TTL for automatic cleanup
            time_to_live_attribute="ttl",
        )

        # GSI for querying executions by status
        self.executions_table.add_global_secondary_index(
            index_name="status-started_at-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="started_at",
                type=dynamodb.AttributeType.STRING,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

    def _create_poll_state_table(self, removal_policy: RemovalPolicy) -> None:
        """Create the PollState table.

        Schema:
        - PK: workflow_id (String)

        Stores state for polling triggers to track what has been processed.
        """
        self.poll_state_table = dynamodb.Table(
            self,
            "PollStateTable",
            table_name=f"{self.environment}-PollState",
            partition_key=dynamodb.Attribute(
                name="workflow_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
        )
```

**Validation:** `cdk synth` generates CloudFormation with 3 tables, correct keys and GSI

### Phase 4: Lambda Directory Structure

#### Step 4.1: Create Lambda Directories
**Files:** `lambdas/`, `lambdas/api/`, `lambdas/actions/`
**Description:** Create directory structure for Lambda functions

```bash
mkdir -p lambdas/api
mkdir -p lambdas/actions
touch lambdas/api/.gitkeep
touch lambdas/actions/.gitkeep
```

**Validation:** Directories exist with .gitkeep files

### Phase 5: Frontend Initialization

#### Step 5.1: Initialize Vite React Project
**Description:** Create React + TypeScript frontend with Vite

```bash
cd /home/juri/projects/automation-platform
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Validation:** `npm run dev` starts development server

#### Step 5.2: Install Frontend Dependencies
**Files:** `frontend/package.json`
**Description:** Add core dependencies for the project

```bash
cd frontend
npm install @tanstack/react-query axios react-router-dom react-hook-form zustand
npm install -D tailwindcss postcss autoprefixer @types/react-router-dom
npx tailwindcss init -p
```

**Validation:** Dependencies in package.json, tailwind.config.js exists

### Phase 6: Verification & Deployment

#### Step 6.1: Set Up CDK Virtual Environment
**Description:** Create and activate Python virtual environment for CDK

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**Validation:** `pip list` shows aws-cdk-lib installed

#### Step 6.2: Synthesize CloudFormation
**Description:** Generate CloudFormation templates

```bash
cd cdk
source .venv/bin/activate
cdk synth
```

**Validation:** `cdk.out/` contains CloudFormation templates for both stacks

#### Step 6.3: Diff and Deploy
**Description:** Review changes and deploy to AWS

```bash
cd cdk
cdk diff
cdk deploy --all --require-approval never
```

**Validation:**
- CloudFormation stacks created in AWS Console
- DynamoDB tables visible in DynamoDB Console
- SSM parameters visible in Systems Manager Console

---

## Testing Requirements

### Unit Tests
- [ ] None required for infrastructure (CDK handles validation)

### Integration Tests
- [ ] `cdk synth` produces valid CloudFormation (CDK built-in validation)
- [ ] `cdk diff` shows expected resources

### Manual Testing
1. Run `cdk synth` and verify no errors
2. Run `cdk deploy --all`
3. Verify in AWS Console:
   - DynamoDB: 3 tables exist with correct schemas
   - SSM: Parameters exist under `/automations/dev/`
   - IAM: Lambda base role exists
4. Run `cd frontend && npm run dev` to verify frontend starts

---

## Error Handling

### Expected Errors
| Error | Cause | Handling |
|-------|-------|----------|
| CDK Bootstrap Required | First CDK deploy to account | Run `cdk bootstrap` |
| Credentials Not Configured | No AWS credentials | Configure AWS CLI |
| Table Already Exists | Re-running with same name | CDK handles updates |

### Edge Cases
1. **Stack update fails:** CDK rollback handles this automatically
2. **Partial deploy:** Re-run `cdk deploy --all` to resume

### Rollback Plan
```bash
# To destroy all resources (dev only):
cdk destroy --all

# To rollback specific stack:
cdk destroy dev-automation-database
```

---

## Performance Considerations

- **DynamoDB on-demand:** No provisioning needed, scales automatically
- **SSM Standard tier:** Sufficient for ~100 parameters, no cost
- **No cold start concerns:** Infrastructure only, no Lambda yet

---

## Security Considerations

- [x] No secrets in code (use SSM SecureString for secrets)
- [x] Least privilege IAM (Lambda role only reads specific paths)
- [x] Point-in-time recovery enabled on critical tables
- [x] DynamoDB encryption at rest (default)
- [ ] Consider adding VPC endpoints for DynamoDB (future optimization)

---

## Cost Impact

| Service | Change | Monthly Impact |
|---------|--------|----------------|
| DynamoDB | 3 tables, on-demand | ~$0-1 (pay per request) |
| SSM | Standard parameters | $0 |
| CloudFormation | Stack management | $0 |

**Total estimated monthly impact:** < $1

---

## Open Questions

1. [x] ~~Auth strategy for API~~ - Deferred to API stack PRP
2. [x] ~~DynamoDB Streams~~ - Only on Workflows table (for reacting to workflow changes like cron trigger updates)
3. [x] ~~Frontend deps~~ - Include react-hook-form and zustand (per CLAUDE.md standards)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Well-defined scope from INITIAL doc, clear data models |
| Feasibility | 10 | Standard CDK patterns, all documented in examples |
| Completeness | 10 | All questions resolved, full spec ready |
| Alignment | 10 | Matches PLANNING.md architecture exactly |
| **Overall** | **9.75** | Ready for implementation |

---

## Changelog

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-12 | Claude | Initial draft |
| 2025-12-12 | Claude | Resolved open questions: Streams only on Workflows table, added react-hook-form and zustand to frontend deps |
