# INITIAL: Project Foundation & CDK Setup

**Date:** 2025-01-XX  
**Priority:** High  
**Phase:** 1

## FEATURE

Set up the foundational AWS infrastructure using CDK, including:
1. CDK project initialization with Python
2. DynamoDB tables for workflows, executions, and poll state
3. Basic project structure for lambdas and frontend
4. Shared IAM roles and SSM parameter paths
5. Deploy and verify the foundation is working

This is the prerequisite for all other features.

## USER STORIES

- As a developer, I want the CDK project initialized so that I can define infrastructure as code
- As a developer, I want DynamoDB tables created so that I can store workflow data
- As a developer, I want a consistent project structure so that future development is organized

## EXAMPLES

- `examples/cdk/lambda_stack.py` - Reference for CDK patterns and Lambda definitions

## DOCUMENTATION

- AWS CDK Python Guide: https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html
- DynamoDB CDK: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb.html
- Internal: `docs/PLANNING.md` - See data models section

## ACCEPTANCE CRITERIA

- [ ] CDK project initialized at `cdk/` with Python
- [ ] `cdk synth` runs without errors
- [ ] DynamoDB `Workflows` table created with correct schema
- [ ] DynamoDB `Executions` table created with correct schema and GSI
- [ ] DynamoDB `PollState` table created with correct schema
- [ ] SSM parameter paths defined for `/automations/config/*` and `/automations/secrets/*`
- [ ] `cdk deploy` succeeds and creates resources in AWS
- [ ] Lambda directory structure created at `lambdas/`
- [ ] Frontend directory initialized with Vite + React + TypeScript

## CONSTRAINTS

- Use on-demand capacity for DynamoDB (pay-per-request)
- Use RemovalPolicy.DESTROY for dev environment (easy cleanup)
- Python 3.11 for Lambda runtime compatibility
- Keep costs minimal - no provisioned capacity

## OUT OF SCOPE

- Lambda function implementations (separate features)
- API Gateway setup (separate feature)
- Frontend implementation beyond initialization
- CI/CD pipeline

## OTHER CONSIDERATIONS

- Make sure to set up `.venv` for the CDK project
- The CDK project needs its own requirements.txt separate from lambdas
- Use `cdk.context.json` for environment-specific config
- Consider using CDK context for account/region rather than hardcoding
- DynamoDB tables should have TTL enabled on executions for automatic cleanup

## RELATED TASKS

- Blocks: All other Phase 1 tasks
- See: `docs/TASK.md` - Phase 1 Foundation tasks

## DATA MODELS

Reference these from `docs/PLANNING.md`:

### Workflows Table
- **PK:** `workflow_id` (String)
- **Attributes:** name, description, enabled, trigger, steps, created_at, updated_at

### Executions Table
- **PK:** `workflow_id` (String)
- **SK:** `execution_id` (String, ULID)
- **Attributes:** status, trigger_data, steps, started_at, finished_at, error
- **GSI:** `status-index` (PK: status, SK: started_at)
- **TTL:** `ttl` attribute for automatic deletion after 90 days

### PollState Table
- **PK:** `workflow_id` (String)
- **Attributes:** last_checked_at, last_content_hash, seen_item_ids, last_error

---

## For Claude

When generating the PRP for this feature:
1. Include exact CDK code for each stack
2. Include the full `app.py` entry point
3. Include `cdk.json` and `requirements.txt`
4. Include directory creation commands
5. Include verification steps (cdk synth, cdk diff, cdk deploy)
6. Reference the data models from PLANNING.md exactly
