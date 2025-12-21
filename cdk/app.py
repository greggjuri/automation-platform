#!/usr/bin/env python3
"""CDK Application entry point for Automation Platform.

This app creates all infrastructure stacks for the automation platform.
Deploy order: shared → database → (api, triggers, execution) → frontend
"""

import os

import aws_cdk as cdk

from stacks.api_stack import ApiStack
from stacks.database_stack import DatabaseStack
from stacks.execution_stack import ExecutionStack
from stacks.frontend_stack import FrontendStack
from stacks.shared_stack import SharedStack
from stacks.triggers_stack import TriggersStack

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

# Execution engine (SQS, Step Functions, Action Lambdas)
# Created before API stack so we can pass execution_queue to API
execution_stack = ExecutionStack(
    app,
    f"{stack_prefix}-execution",
    workflows_table=database_stack.workflows_table,
    executions_table=database_stack.executions_table,
    environment=environment,
    env=env,
)

# Triggers (Cron Handler and Poller Lambdas for EventBridge scheduled rules)
# Created before API stack so we can pass handler ARNs
triggers_stack = TriggersStack(
    app,
    f"{stack_prefix}-triggers",
    workflows_table=database_stack.workflows_table,
    poll_state_table=database_stack.poll_state_table,
    execution_queue=execution_stack.execution_queue,
    environment=environment,
    env=env,
)

# API Gateway and Lambda
api_stack = ApiStack(
    app,
    f"{stack_prefix}-api",
    workflows_table=database_stack.workflows_table,
    executions_table=database_stack.executions_table,
    execution_queue=execution_stack.execution_queue,
    cron_handler_arn=triggers_stack.cron_handler.function_arn,
    poller_arn=triggers_stack.poller.function_arn,
    environment=environment,
    env=env,
)

# Frontend (S3, CloudFront, Route 53)
frontend_stack = FrontendStack(
    app,
    f"{stack_prefix}-frontend",
    domain_name="automations.jurigregg.com",
    hosted_zone_id="Z0064626MF3NMWPFKM6S",  # jurigregg.com hosted zone
    hosted_zone_name="jurigregg.com",
    certificate_arn="arn:aws:acm:us-east-1:490004610151:certificate/ada55692-5653-49e3-bbcc-ea841060a763",
    environment=environment,
    env=env,
)

# Add tags to all resources
cdk.Tags.of(app).add("Project", "AutomationPlatform")
cdk.Tags.of(app).add("Environment", environment)
cdk.Tags.of(app).add("ManagedBy", "CDK")

app.synth()
