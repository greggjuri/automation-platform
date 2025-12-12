"""
Example: CDK Stack for Lambda + API Gateway

This example demonstrates the standard pattern for CDK stacks that create
Lambda functions with API Gateway integration. Use this as a template
for new feature stacks.

Key patterns:
- Lambda function with bundled dependencies
- HTTP API with Lambda integration
- Environment variables for configuration
- IAM roles with least privilege
- Proper construct organization

Copy this file and adapt for your specific infrastructure needs.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

if TYPE_CHECKING:
    from aws_cdk import Environment


class ApiStack(Stack):
    """CDK Stack for API Gateway and Lambda functions.

    This stack creates:
    - A Lambda function for handling API requests
    - An HTTP API Gateway with routes
    - DynamoDB table access permissions
    - CloudWatch log groups

    Attributes:
        api: The HTTP API Gateway construct
        api_handler: The Lambda function handling requests
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: dynamodb.ITable,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the API stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            table: DynamoDB table for data storage
            environment: Deployment environment (dev, staging, prod)
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        # ---------------------------------------------------------------------
        # Lambda Function
        # ---------------------------------------------------------------------

        # Create log group with retention policy
        log_group = logs.LogGroup(
            self,
            "ApiHandlerLogs",
            log_group_name=f"/aws/lambda/{environment}-api-handler",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Lambda function for API handling
        self.api_handler = lambda_.Function(
            self,
            "ApiHandler",
            function_name=f"{environment}-api-handler",
            description="Handles API Gateway requests for workflow operations",
            # Runtime and code
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "..", "..", "lambdas", "api"),
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            # Resource configuration
            memory_size=256,
            timeout=Duration.seconds(29),  # API Gateway max is 29s
            # Environment variables
            environment={
                "TABLE_NAME": table.table_name,
                "ENVIRONMENT": environment,
                "POWERTOOLS_SERVICE_NAME": "api-handler",
                "POWERTOOLS_LOG_LEVEL": "INFO" if environment == "prod" else "DEBUG",
                "POWERTOOLS_METRICS_NAMESPACE": "AutomationPlatform",
            },
            # Logging
            log_group=log_group,
            # Tracing
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Grant DynamoDB permissions
        table.grant_read_write_data(self.api_handler)

        # ---------------------------------------------------------------------
        # HTTP API Gateway
        # ---------------------------------------------------------------------

        # Create HTTP API
        self.api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name=f"{environment}-automation-api",
            description="Automation Platform API",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_origins=["*"] if environment != "prod" else ["https://automations.jurigregg.com"],
                max_age=Duration.hours(1),
            ),
        )

        # Lambda integration
        api_integration = integrations.HttpLambdaIntegration(
            "ApiIntegration",
            handler=self.api_handler,
        )

        # ---------------------------------------------------------------------
        # API Routes
        # ---------------------------------------------------------------------

        # Workflow routes
        self.api.add_routes(
            path="/workflows",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
            integration=api_integration,
        )

        self.api.add_routes(
            path="/workflows/{workflow_id}",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.PUT, apigwv2.HttpMethod.DELETE],
            integration=api_integration,
        )

        # Execution routes
        self.api.add_routes(
            path="/workflows/{workflow_id}/executions",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        self.api.add_routes(
            path="/executions/{execution_id}",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        # Test/trigger route
        self.api.add_routes(
            path="/workflows/{workflow_id}/test",
            methods=[apigwv2.HttpMethod.POST],
            integration=api_integration,
        )

        # Health check
        self.api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )


# -----------------------------------------------------------------------------
# Example: Action Lambda Stack
# -----------------------------------------------------------------------------


class ActionLambdaStack(Stack):
    """CDK Stack for Step Functions action Lambdas.

    This stack creates Lambda functions that execute as tasks
    within Step Functions workflows.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str = "dev",
        **kwargs,
    ) -> None:
        """Initialize the action Lambda stack.

        Args:
            scope: The parent construct
            construct_id: Unique identifier for this stack
            environment: Deployment environment
            **kwargs: Additional stack options
        """
        super().__init__(scope, construct_id, **kwargs)

        # ---------------------------------------------------------------------
        # HTTP Request Action Lambda
        # ---------------------------------------------------------------------

        self.http_request_action = self._create_action_lambda(
            name="http-request",
            description="Executes HTTP requests in workflows",
            handler="action.handler",
            code_path="http_request",
            environment=environment,
            timeout_seconds=30,
        )

        # ---------------------------------------------------------------------
        # Transform Action Lambda
        # ---------------------------------------------------------------------

        self.transform_action = self._create_action_lambda(
            name="transform",
            description="Transforms data using templates",
            handler="action.handler",
            code_path="transform",
            environment=environment,
            timeout_seconds=10,
        )

        # ---------------------------------------------------------------------
        # Notify Action Lambda
        # ---------------------------------------------------------------------

        self.notify_action = self._create_action_lambda(
            name="notify",
            description="Sends notifications (Discord, email)",
            handler="action.handler",
            code_path="notify",
            environment=environment,
            timeout_seconds=15,
        )

    def _create_action_lambda(
        self,
        name: str,
        description: str,
        handler: str,
        code_path: str,
        environment: str,
        timeout_seconds: int = 30,
        memory_mb: int = 256,
    ) -> lambda_.Function:
        """Create a standardized action Lambda function.

        Args:
            name: Action name (used in function name)
            description: Human-readable description
            handler: Handler function path
            code_path: Path to Lambda code directory
            environment: Deployment environment
            timeout_seconds: Function timeout
            memory_mb: Memory allocation

        Returns:
            The created Lambda function
        """
        function_name = f"{environment}-action-{name}"

        # Log group
        log_group = logs.LogGroup(
            self,
            f"{name}Logs",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Lambda function
        fn = lambda_.Function(
            self,
            f"{name}Action",
            function_name=function_name,
            description=description,
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler=handler,
            code=lambda_.Code.from_asset(
                path=os.path.join(
                    os.path.dirname(__file__), "..", "..", "lambdas", "actions", code_path
                ),
                bundling={
                    "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            memory_size=memory_mb,
            timeout=Duration.seconds(timeout_seconds),
            environment={
                "ENVIRONMENT": environment,
                "POWERTOOLS_SERVICE_NAME": f"action-{name}",
                "POWERTOOLS_LOG_LEVEL": "INFO" if environment == "prod" else "DEBUG",
            },
            log_group=log_group,
            tracing=lambda_.Tracing.ACTIVE,
        )

        return fn


# -----------------------------------------------------------------------------
# Example: App Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    """Example of how to use these stacks in your CDK app.

    This is not meant to be run directly, but shows the pattern
    for composing stacks in app.py.
    """
    from aws_cdk import App

    app = App()

    # Get environment from context
    environment = app.node.try_get_context("environment") or "dev"

    # Create database stack first (not shown, but required)
    # database_stack = DatabaseStack(app, f"{environment}-database")

    # Create API stack
    # api_stack = ApiStack(
    #     app,
    #     f"{environment}-api",
    #     table=database_stack.workflows_table,
    #     environment=environment,
    # )

    # Create action Lambda stack
    # action_stack = ActionLambdaStack(
    #     app,
    #     f"{environment}-actions",
    #     environment=environment,
    # )

    app.synth()
